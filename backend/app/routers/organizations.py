from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_org, get_current_user, get_db
from app.models.organization import Organization
from app.models.user import User
from app.schemas.organization import (
    InviteCreateRequest,
    InviteResponse,
    MemberResponse,
    OrgResponse,
    OrgUpdateRequest,
)
from app.services.auth_service import create_invite

router = APIRouter(prefix="/api/v1/org", tags=["organization"])


@router.get("", response_model=OrgResponse)
async def get_org(org: Organization = Depends(get_current_org)):
    return org


@router.patch("", response_model=OrgResponse)
async def update_org(
    payload: OrgUpdateRequest,
    org: Organization = Depends(get_current_org),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if user.role not in ("owner", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
        )
    if payload.name is not None:
        org.name = payload.name
    if payload.company_profile is not None:
        org.company_profile = payload.company_profile
    if payload.capability_statement is not None:
        org.capability_statement = payload.capability_statement
    await db.commit()
    await db.refresh(org)
    return org


@router.get("/members", response_model=list[MemberResponse])
async def list_members(
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User).where(User.org_id == org.id).order_by(User.created_at)
    )
    return result.scalars().all()


@router.post(
    "/invites", response_model=InviteResponse, status_code=status.HTTP_201_CREATED
)
async def send_invite(
    payload: InviteCreateRequest,
    org: Organization = Depends(get_current_org),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if user.role not in ("owner", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
        )
    invite = await create_invite(
        db=db,
        org_id=org.id,
        email=payload.email,
        role=payload.role,
        invited_by=user.id,
    )
    return invite


@router.delete("/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    member_id: uuid.UUID,
    org: Organization = Depends(get_current_org),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if user.role not in ("owner", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
        )
    result = await db.execute(
        select(User).where(User.id == member_id, User.org_id == org.id)
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Member not found"
        )
    if member.role == "owner":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot remove owner"
        )
    member.is_active = False
    await db.commit()
