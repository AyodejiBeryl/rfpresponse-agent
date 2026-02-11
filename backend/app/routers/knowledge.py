from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_org, get_current_user, get_db, get_llm_client
from app.models.organization import Organization
from app.models.user import User
from app.schemas.knowledge import (
    KnowledgeDocDetail,
    KnowledgeDocResponse,
    KnowledgeSearchRequest,
    KnowledgeSearchResult,
)
from app.services.knowledge_service import (
    delete_document,
    get_document,
    list_documents,
    search_knowledge,
    upload_and_index,
)
from app.services.llm_client import LLMClient

router = APIRouter(prefix="/api/v1/knowledge", tags=["knowledge"])


@router.get("", response_model=list[KnowledgeDocResponse])
async def list_knowledge(
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    docs = await list_documents(db, org.id)
    return docs


@router.post(
    "", response_model=KnowledgeDocResponse, status_code=status.HTTP_201_CREATED
)
async def upload_knowledge(
    file: UploadFile = File(...),
    title: str = Form(...),
    doc_type: str = Form(default="other"),
    org: Organization = Depends(get_current_org),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    llm: LLMClient = Depends(get_llm_client),
):
    if doc_type not in (
        "company_profile",
        "past_proposal",
        "capability_statement",
        "past_performance",
        "other",
    ):
        raise HTTPException(status_code=400, detail="Invalid doc_type")

    data = await file.read()
    filename = file.filename or "upload.txt"

    try:
        doc = await upload_and_index(
            db=db,
            org_id=org.id,
            user_id=user.id,
            title=title,
            doc_type=doc_type,
            filename=filename,
            file_data=data,
            llm_client=llm,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return doc


@router.get("/{doc_id}", response_model=KnowledgeDocDetail)
async def get_knowledge_doc(
    doc_id: uuid.UUID,
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    doc = await get_document(db, doc_id, org.id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_knowledge_doc(
    doc_id: uuid.UUID,
    org: Organization = Depends(get_current_org),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if user.role not in ("owner", "admin"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    deleted = await delete_document(db, doc_id, org.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found")


@router.post("/search", response_model=list[KnowledgeSearchResult])
async def search_knowledge_endpoint(
    payload: KnowledgeSearchRequest,
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
    llm: LLMClient = Depends(get_llm_client),
):
    results = await search_knowledge(
        db=db,
        org_id=org.id,
        query=payload.query,
        llm_client=llm,
        top_k=payload.top_k,
    )
    return results
