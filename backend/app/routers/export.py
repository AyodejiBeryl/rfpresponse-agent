from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_org, get_db
from app.models.draft_section import DraftSection
from app.models.organization import Organization
from app.models.project import Project
from app.schemas.analysis import AnalysisResponse, ComplianceRow, RequirementItem
from app.services.exporter import export_csv, export_docx, export_markdown

router = APIRouter(prefix="/api/v1/projects/{project_id}/export", tags=["export"])


async def _load_analysis(db: AsyncSession, project_id: uuid.UUID, org_id: uuid.UUID) -> AnalysisResponse:
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.org_id == org_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    sec_result = await db.execute(
        select(DraftSection).where(
            DraftSection.project_id == project.id,
            DraftSection.is_current == True,
        )
    )
    sections = {s.section_key: s.content for s in sec_result.scalars().all()}

    return AnalysisResponse(
        disclaimer="AI-generated draft; human review required.",
        metadata=project.metadata_json,
        requirements=[RequirementItem(**r) for r in project.requirements],
        compliance_matrix=[ComplianceRow(**m) for m in project.compliance_matrix],
        draft_sections=sections,
        gaps=project.gaps,
    )


@router.post("/csv")
async def export_csv_endpoint(
    project_id: uuid.UUID,
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    analysis = await _load_analysis(db, project_id, org.id)
    csv_text = export_csv(analysis.compliance_matrix)
    return StreamingResponse(
        iter([csv_text.encode("utf-8")]),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="compliance_matrix.csv"'},
    )


@router.post("/markdown")
async def export_markdown_endpoint(
    project_id: uuid.UUID,
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    analysis = await _load_analysis(db, project_id, org.id)
    md = export_markdown(analysis)
    return StreamingResponse(
        iter([md.encode("utf-8")]),
        media_type="text/markdown",
        headers={"Content-Disposition": 'attachment; filename="proposal_draft.md"'},
    )


@router.post("/docx")
async def export_docx_endpoint(
    project_id: uuid.UUID,
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    analysis = await _load_analysis(db, project_id, org.id)
    docx_bytes = export_docx(analysis)
    return StreamingResponse(
        iter([docx_bytes]),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": 'attachment; filename="proposal_draft.docx"'},
    )
