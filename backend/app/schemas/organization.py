from __future__ import annotations
from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field


class OrgResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    company_profile: Optional[str]
    capability_statement: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class OrgUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    company_profile: Optional[str] = None
    capability_statement: Optional[str] = None


class InviteCreateRequest(BaseModel):
    email: EmailStr
    role: str = "member"


class InviteResponse(BaseModel):
    id: UUID
    email: str
    role: str
    token: str
    expires_at: datetime

    model_config = {"from_attributes": True}


class MemberResponse(BaseModel):
    id: UUID
    email: str
    full_name: str
    role: str
    is_active: bool

    model_config = {"from_attributes": True}
