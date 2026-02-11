from __future__ import annotations

import json
import uuid
from typing import List

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
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

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])


def _run_analysis(
    solicitation_text: str,
    company_name: str | None,
    company_profile: str,
    past_performance: list[str],
    capability_statement: str | None,
    knowledge_chunks: list[dict] | None = None,
) -> dict:
    if len(solicitation_text.strip()) < 250:
        raise HTTPException(status_code=400, detail="Solicitation text is too short.")

    metadata = extract_metadata(solicitation_text)
    requirements = extract_requirements(solicitation_text)
    matrix = build_compliance_matrix(
        requirements=requirements,
        company_profile=company_profile,
        past_performance=past_performance,
        capability_statement=capability_statement,
        knowledge_chunks=knowledge_chunks,
    )
    gaps = build_gaps(matrix)
    draft_sections = build_draft_sections(
        metadata=metadata,
        requirements=requirements,
        matrix=matrix,
        company_profile=company_profile,
        past_performance=past_performance,
        company_name=company_name,
    )
    return {
        "metadata": metadata,
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
        pass  # Knowledge base is optional; continue without it

    analysis = _run_analysis(
        solicitation_text=payload.solicitation_text,
        company_name=payload.company_name,
        company_profile=company_profile,
        past_performance=payload.past_performance,
        capability_statement=capability,
        knowledge_chunks=knowledge_chunks,
    )

    project = Project(
        org_id=org.id,
        created_by=user.id,
        title=payload.title,
        status="draft",
        solicitation_text=payload.solicitation_text,
        metadata_json=analysis["metadata"],
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


@router.post("/upload", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project_from_file(
    file: UploadFile = File(...),
    title: str = Form(...),
    company_profile: str = Form(...),
    company_name: str | None = Form(default=None),
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
        raise HTTPException(status_code=400, detail="Unsupported file type. Use PDF, DOCX, or TXT.")

    past_performance: List[str] = []
    if past_performance_json:
        try:
            parsed = json.loads(past_performance_json)
            if isinstance(parsed, list):
                past_performance = [str(item) for item in parsed]
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail=f"Invalid past_performance_json: {exc}")

    profile = company_profile or org.company_profile or ""
    cap = capability_statement or org.capability_statement

    # Retrieve relevant knowledge base chunks
    knowledge_chunks = []
    try:
        knowledge_chunks = await search_knowledge(
            db=db, org_id=org.id, query=text[:1000], llm_client=llm, top_k=10
        )
    except Exception:
        pass

    analysis = _run_analysis(
        solicitation_text=text,
        company_name=company_name,
        company_profile=profile,
        past_performance=past_performance,
        capability_statement=cap,
        knowledge_chunks=knowledge_chunks,
    )

    project = Project(
        org_id=org.id,
        created_by=user.id,
        title=title,
        status="draft",
        solicitation_text=text,
        original_filename=file.filename,
        metadata_json=analysis["metadata"],
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


async def _get_project_or_404(db: AsyncSession, project_id: uuid.UUID, org_id: uuid.UUID) -> Project:
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.org_id == org_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


async def _get_current_sections(db: AsyncSession, project_id: uuid.UUID) -> dict[str, str]:
    result = await db.execute(
        select(DraftSection)
        .where(DraftSection.project_id == project_id, DraftSection.is_current == True)
    )
    sections = result.scalars().all()
    return {s.section_key: s.content for s in sections}


def _build_project_response(project: Project, draft_sections: dict[str, str]) -> ProjectResponse:
    return ProjectResponse(
        id=project.id,
        title=project.title,
        status=project.status,
        metadata_json=project.metadata_json,
        requirements=project.requirements,
        compliance_matrix=project.compliance_matrix,
        gaps=project.gaps,
        draft_sections=draft_sections,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )
