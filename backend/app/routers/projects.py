from __future__ import annotations

import io
import json
import uuid
from typing import List

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_org, get_current_user, get_db, get_llm_client
from app.models.draft_section import DraftSection
from app.models.organization import Organization
from app.models.project import Project
from app.models.user import User
from app.schemas.project import (
    ProjectCreateRequest,
    ProjectListItem,
    ProjectResponse,
    ProjectUpdateRequest,
)
from app.services.drafting import build_draft_sections
from app.services.matrix import build_compliance_matrix, build_gaps
from app.services.knowledge_service import search_knowledge
from app.services.llm_client import LLMClient
from app.services.parser import (
    extract_metadata,
    extract_requirements,
    extract_text_from_docx_bytes,
    extract_text_from_pdf_bytes,
)
from app.services.export_service import create_rfp_response_document
from app.services.llm_parser import (
    extract_metadata_with_llm,
    extract_sections_with_llm,
    extract_requirements_with_llm,
    detect_rfp_type,
)
from app.schemas.rfp_types import RFPType

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])


async def _run_analysis(
    solicitation_text: str,
    company_name: str | None,
    company_profile: str,
    past_performance: list[str],
    capability_statement: str | None,
    knowledge_chunks: list[dict] | None = None,
    rfp_type: RFPType | None = None,
    llm_client: LLMClient | None = None,
    use_llm_extraction: bool = True,
) -> dict:
    """
    Run analysis on RFP document.

    If use_llm_extraction is True and llm_client is provided, uses LLM-based
    extraction for metadata, sections, and requirements. Otherwise, falls back
    to regex-based extraction.
    """
    if len(solicitation_text.strip()) < 250:
        raise HTTPException(status_code=400, detail="Solicitation text is too short.")

    # Determine RFP type if not provided
    detected_rfp_type = rfp_type
    if detected_rfp_type is None and llm_client and use_llm_extraction:
        detected_rfp_type = await detect_rfp_type(solicitation_text, llm_client)
    elif detected_rfp_type is None:
        detected_rfp_type = RFPType.GOVERNMENT_RFP  # Default fallback

    # Extract metadata
    if llm_client and use_llm_extraction:
        # Use LLM-based extraction
        extracted_metadata = await extract_metadata_with_llm(
            solicitation_text, detected_rfp_type, llm_client
        )
        metadata = {
            "document_type": extracted_metadata.document_type or "",
            "title": extracted_metadata.title or "",
            "solicitation_number": extracted_metadata.reference_number or "Not found",
            "due_date": extracted_metadata.due_date or "Not found",
            "issuing_organization": extracted_metadata.issuing_organization or "",
            "naics": extracted_metadata.naics_code or "Not found",
            "psc": extracted_metadata.psc_code or "Not found",
            "set_aside": extracted_metadata.set_aside or "",
            "contact_name": extracted_metadata.contact_name or "",
            "contact_email": extracted_metadata.contact_email or "",
            "page_limit": str(extracted_metadata.page_limit) if extracted_metadata.page_limit else "",
            "file_format": extracted_metadata.file_format or "",
        }

        # Extract sections
        detected_sections = await extract_sections_with_llm(
            solicitation_text, detected_rfp_type, llm_client
        )

        # Extract requirements with LLM
        enhanced_requirements = await extract_requirements_with_llm(
            solicitation_text, detected_sections, detected_rfp_type, llm_client
        )

        # Convert enhanced requirements to the format expected by compliance matrix
        from app.schemas.analysis import RequirementItem
        requirements = [
            RequirementItem(
                id=req.id,
                section=req.source_section or "General",
                requirement_text=req.requirement_text,
                priority=req.priority.value if hasattr(req.priority, 'value') else req.priority,
                source_reference=req.source_reference,
            )
            for req in enhanced_requirements
        ]
    else:
        # Fall back to regex-based extraction
        metadata = extract_metadata(solicitation_text)
        requirements = extract_requirements(solicitation_text)
        detected_sections = []

    # Build compliance matrix (using existing function for now)
    matrix = build_compliance_matrix(
        requirements=requirements,
        company_profile=company_profile,
        past_performance=past_performance,
        capability_statement=capability_statement,
        knowledge_chunks=knowledge_chunks,
    )
    gaps = build_gaps(matrix)

    # Build draft sections
    draft_sections = build_draft_sections(
        metadata=metadata,
        requirements=requirements,
        matrix=matrix,
        company_profile=company_profile,
        past_performance=past_performance,
        company_name=company_name,
    )

    return {
        "rfp_type": detected_rfp_type.value if detected_rfp_type else None,
        "metadata": metadata,
        "detected_sections": [s.model_dump() for s in detected_sections],
        "requirements": [r.model_dump() for r in requirements],
        "compliance_matrix": [m.model_dump() for m in matrix],
        "gaps": gaps,
        "draft_sections": draft_sections,
    }


@router.get("", response_model=list[ProjectListItem])
async def list_projects(
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Project)
        .where(Project.org_id == org.id)
        .order_by(Project.created_at.desc())
    )
    return result.scalars().all()


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: ProjectCreateRequest,
    org: Organization = Depends(get_current_org),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    llm: LLMClient = Depends(get_llm_client),
):
    company_profile = payload.company_profile or org.company_profile or ""
    capability = payload.capability_statement or org.capability_statement

    # Retrieve relevant knowledge base chunks for enhanced compliance matching
    knowledge_chunks = []
    try:
        knowledge_chunks = await search_knowledge(
            db=db,
            org_id=org.id,
            query=payload.solicitation_text[:1000],
            llm_client=llm,
            top_k=10,
        )
    except Exception:
        await db.rollback()  # Reset poisoned transaction

    # Run analysis with LLM-based extraction
    analysis = await _run_analysis(
        solicitation_text=payload.solicitation_text,
        company_name=payload.company_name,
        company_profile=company_profile,
        past_performance=payload.past_performance,
        capability_statement=capability,
        knowledge_chunks=knowledge_chunks,
        rfp_type=payload.rfp_type,
        llm_client=llm,
        use_llm_extraction=True,
    )

    project = Project(
        org_id=org.id,
        created_by=user.id,
        title=payload.title,
        status="draft",
        rfp_type=analysis.get("rfp_type"),
        solicitation_text=payload.solicitation_text,
        metadata_json=analysis["metadata"],
        detected_sections=analysis.get("detected_sections", []),
        requirements=analysis["requirements"],
        compliance_matrix=analysis["compliance_matrix"],
        gaps=analysis["gaps"],
        company_profile_snapshot=company_profile,
        past_performance_snapshot=payload.past_performance,
        capability_statement_snapshot=capability,
    )
    db.add(project)
    await db.flush()

    # Save draft sections
    for key, content in analysis["draft_sections"].items():
        section = DraftSection(
            project_id=project.id,
            section_key=key,
            content=content,
            version=1,
            is_current=True,
            created_by=user.id,
        )
        db.add(section)

    await db.commit()
    await db.refresh(project)

    return _build_project_response(project, analysis["draft_sections"])


@router.post(
    "/upload", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED
)
async def create_project_from_file(
    file: UploadFile = File(...),
    title: str = Form(...),
    company_profile: str = Form(...),
    company_name: str | None = Form(default=None),
    rfp_type: str | None = Form(default=None),
    past_performance_json: str | None = Form(default=None),
    capability_statement: str | None = Form(default=None),
    org: Organization = Depends(get_current_org),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    llm: LLMClient = Depends(get_llm_client),
):
    data = await file.read()
    suffix = (file.filename or "").lower()

    if suffix.endswith(".pdf"):
        text = extract_text_from_pdf_bytes(data)
    elif suffix.endswith(".docx"):
        text = extract_text_from_docx_bytes(data)
    elif suffix.endswith(".txt"):
        text = data.decode("utf-8", errors="ignore")
    else:
        raise HTTPException(
            status_code=400, detail="Unsupported file type. Use PDF, DOCX, or TXT."
        )

    past_performance: List[str] = []
    if past_performance_json:
        try:
            parsed = json.loads(past_performance_json)
            if isinstance(parsed, list):
                past_performance = [str(item) for item in parsed]
        except json.JSONDecodeError as exc:
            raise HTTPException(
                status_code=400, detail=f"Invalid past_performance_json: {exc}"
            )

    profile = company_profile or org.company_profile or ""
    cap = capability_statement or org.capability_statement

    # Retrieve relevant knowledge base chunks
    knowledge_chunks = []
    try:
        knowledge_chunks = await search_knowledge(
            db=db, org_id=org.id, query=text[:1000], llm_client=llm, top_k=10
        )
    except Exception:
        await db.rollback()  # Reset poisoned transaction

    # Parse rfp_type if provided
    parsed_rfp_type = None
    if rfp_type:
        try:
            parsed_rfp_type = RFPType(rfp_type)
        except ValueError:
            pass  # Invalid type, will auto-detect

    # Run analysis with LLM-based extraction
    analysis = await _run_analysis(
        solicitation_text=text,
        company_name=company_name,
        company_profile=profile,
        past_performance=past_performance,
        capability_statement=cap,
        knowledge_chunks=knowledge_chunks,
        rfp_type=parsed_rfp_type,
        llm_client=llm,
        use_llm_extraction=True,
    )

    project = Project(
        org_id=org.id,
        created_by=user.id,
        title=title,
        status="draft",
        rfp_type=analysis.get("rfp_type"),
        solicitation_text=text,
        original_filename=file.filename,
        metadata_json=analysis["metadata"],
        detected_sections=analysis.get("detected_sections", []),
        requirements=analysis["requirements"],
        compliance_matrix=analysis["compliance_matrix"],
        gaps=analysis["gaps"],
        company_profile_snapshot=profile,
        past_performance_snapshot=past_performance,
        capability_statement_snapshot=cap,
    )
    db.add(project)
    await db.flush()

    for key, content in analysis["draft_sections"].items():
        section = DraftSection(
            project_id=project.id,
            section_key=key,
            content=content,
            version=1,
            is_current=True,
            created_by=user.id,
        )
        db.add(section)

    await db.commit()
    await db.refresh(project)

    return _build_project_response(project, analysis["draft_sections"])


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: uuid.UUID,
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    project = await _get_project_or_404(db, project_id, org.id)
    sections = await _get_current_sections(db, project.id)
    return _build_project_response(project, sections)


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: uuid.UUID,
    payload: ProjectUpdateRequest,
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    project = await _get_project_or_404(db, project_id, org.id)
    if payload.title is not None:
        project.title = payload.title
    if payload.status is not None:
        project.status = payload.status
    await db.commit()
    await db.refresh(project)
    sections = await _get_current_sections(db, project.id)
    return _build_project_response(project, sections)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: uuid.UUID,
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    project = await _get_project_or_404(db, project_id, org.id)
    project.status = "archived"
    await db.commit()


@router.post("/{project_id}/export/{format}")
async def export_project(
    project_id: uuid.UUID,
    format: str,
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    """Export project RFP response in various formats: docx, csv, markdown."""
    project = await _get_project_or_404(db, project_id, org.id)
    sections = await _get_current_sections(db, project.id)

    # Create safe filename from project title
    safe_title = "".join(c for c in project.title if c.isalnum() or c in (' ', '-', '_')).strip()

    if format == "docx":
        # Get company name from profile snapshot
        company_name = None
        if project.company_profile_snapshot:
            first_line = project.company_profile_snapshot.split('\n')[0]
            if len(first_line) < 100:
                company_name = first_line.strip()

        # Generate the Word document
        doc_bytes = create_rfp_response_document(
            title=project.title,
            metadata=project.metadata_json or {},
            draft_sections=sections,
            requirements=project.requirements,
            compliance_matrix=project.compliance_matrix,
            company_name=company_name,
        )

        return StreamingResponse(
            io.BytesIO(doc_bytes),
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f'attachment; filename="{safe_title[:50]}_Response.docx"'},
        )

    elif format == "csv":
        # Export compliance matrix as CSV
        import csv
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Requirement ID", "Status", "Evidence", "Owner", "Notes"])
        for row in project.compliance_matrix:
            writer.writerow([
                row.get("requirement_id", ""),
                row.get("status", ""),
                row.get("evidence", ""),
                row.get("owner", ""),
                row.get("notes", ""),
            ])
        csv_content = output.getvalue()

        return StreamingResponse(
            io.BytesIO(csv_content.encode("utf-8")),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{safe_title[:50]}_Compliance_Matrix.csv"'},
        )

    elif format == "markdown":
        # Export draft sections as Markdown
        md_content = f"# {project.title}\n\n"

        # Add metadata
        if project.metadata_json:
            md_content += "## Document Information\n\n"
            for key, value in project.metadata_json.items():
                if value and value != "Not found" and value != "N/A":
                    md_content += f"- **{key.replace('_', ' ').title()}**: {value}\n"
            md_content += "\n"

        # Add draft sections
        section_order = [
            ("executive_summary", "Executive Summary"),
            ("technical_approach", "Technical Approach"),
            ("management_approach", "Management Approach"),
            ("past_performance", "Past Performance"),
            ("staffing_plan", "Staffing Plan"),
            ("pricing_summary", "Pricing Summary"),
        ]

        for section_key, section_title in section_order:
            if section_key in sections and sections[section_key]:
                md_content += f"## {section_title}\n\n{sections[section_key]}\n\n"

        # Add any remaining sections
        for key, content in sections.items():
            if key not in [s[0] for s in section_order] and content:
                title = key.replace('_', ' ').title()
                md_content += f"## {title}\n\n{content}\n\n"

        return StreamingResponse(
            io.BytesIO(md_content.encode("utf-8")),
            media_type="text/markdown",
            headers={"Content-Disposition": f'attachment; filename="{safe_title[:50]}_Proposal.md"'},
        )

    else:
        raise HTTPException(status_code=400, detail=f"Unsupported export format: {format}")


async def _get_project_or_404(
    db: AsyncSession, project_id: uuid.UUID, org_id: uuid.UUID
) -> Project:
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.org_id == org_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
        )
    return project


async def _get_current_sections(
    db: AsyncSession, project_id: uuid.UUID
) -> dict[str, str]:
    result = await db.execute(
        select(DraftSection).where(
            DraftSection.project_id == project_id, DraftSection.is_current.is_(True)
        )
    )
    sections = result.scalars().all()
    return {s.section_key: s.content for s in sections}


def _build_project_response(
    project: Project, draft_sections: dict[str, str]
) -> ProjectResponse:
    return ProjectResponse(
        id=project.id,
        title=project.title,
        status=project.status,
        rfp_type=project.rfp_type,
        metadata_json=project.metadata_json,
        detected_sections=project.detected_sections or [],
        requirements=project.requirements,
        compliance_matrix=project.compliance_matrix,
        gaps=project.gaps,
        draft_sections=draft_sections,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )
