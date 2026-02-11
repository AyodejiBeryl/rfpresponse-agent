from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class KnowledgeDocResponse(BaseModel):
    id: UUID
    title: str
    doc_type: str
    original_filename: Optional[str]
    is_indexed: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class KnowledgeDocDetail(BaseModel):
    id: UUID
    title: str
    doc_type: str
    original_filename: Optional[str]
    extracted_text: Optional[str]
    is_indexed: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class KnowledgeSearchRequest(BaseModel):
    query: str = Field(..., min_length=3)
    top_k: int = Field(default=5, ge=1, le=20)


class KnowledgeSearchResult(BaseModel):
    chunk_id: str
    chunk_text: str
    document_id: str
    doc_title: str
    similarity: float
