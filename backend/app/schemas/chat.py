from __future__ import annotations
from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field


class ConversationCreateRequest(BaseModel):
    title: Optional[str] = None
    section_key: Optional[str] = None


class ConversationResponse(BaseModel):
    id: UUID
    project_id: UUID
    title: Optional[str]
    section_key: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class SendMessageRequest(BaseModel):
    content: str = Field(..., min_length=1)


class MessageResponse(BaseModel):
    id: UUID
    conversation_id: UUID
    role: str
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}
