from __future__ import annotations
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    org_name: str = Field(..., min_length=2, max_length=255)
    full_name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=8)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class InviteAcceptRequest(BaseModel):
    token: str
    full_name: str = Field(..., min_length=2, max_length=255)
    password: str = Field(..., min_length=8)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: UUID
    org_id: UUID
    role: str


class UserResponse(BaseModel):
    id: UUID
    email: str
    full_name: str
    org_id: UUID
    role: str

    model_config = {"from_attributes": True}
