from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.auth import (
    InviteAcceptRequest,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.services.auth_service import (
    accept_invite,
    authenticate_user,
    create_access_token,
    create_refresh_token,
    register_org_and_user,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, db: AsyncSession = Depends(get_db)):
    try:
        org, user = await register_org_and_user(
            db=db,
            org_name=payload.org_name,
            full_name=payload.full_name,
            email=payload.email,
            password=payload.password,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))

    return TokenResponse(
        access_token=create_access_token(user.id, org.id),
        user_id=user.id,
        org_id=org.id,
        role=user.role,
    )


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    user = await authenticate_user(db, payload.email, payload.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    return TokenResponse(
        access_token=create_access_token(user.id, user.org_id),
        user_id=user.id,
        org_id=user.org_id,
        role=user.role,
    )


@router.post("/invite/accept", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def invite_accept(payload: InviteAcceptRequest, db: AsyncSession = Depends(get_db)):
    try:
        user, invite = await accept_invite(
            db=db,
            token=payload.token,
            full_name=payload.full_name,
            password=payload.password,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    return TokenResponse(
        access_token=create_access_token(user.id, user.org_id),
        user_id=user.id,
        org_id=user.org_id,
        role=user.role,
    )


@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)):
    return user
