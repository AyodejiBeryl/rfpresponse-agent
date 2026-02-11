from __future__ import annotations

import re
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.invite import Invite
from app.models.organization import Organization
from app.models.user import User

ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    pw_bytes = password.encode("utf-8")[:72]
    return bcrypt.hashpw(pw_bytes, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    pw_bytes = plain.encode("utf-8")[:72]
    return bcrypt.checkpw(pw_bytes, hashed.encode("utf-8"))


def create_access_token(user_id: uuid.UUID, org_id: uuid.UUID) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    payload = {
        "sub": str(user_id),
        "org": str(org_id),
        "exp": expire,
        "type": "access",
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def create_refresh_token(user_id: uuid.UUID, org_id: uuid.UUID) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.refresh_token_expire_days
    )
    payload = {
        "sub": str(user_id),
        "org": str(org_id),
        "exp": expire,
        "type": "refresh",
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug[:100]


async def register_org_and_user(
    db: AsyncSession,
    org_name: str,
    full_name: str,
    email: str,
    password: str,
) -> tuple[Organization, User]:
    # Check email uniqueness
    existing = await db.execute(select(User).where(User.email == email))
    if existing.scalar_one_or_none():
        raise ValueError("Email already registered")

    org = Organization(
        name=org_name, slug=_slugify(org_name) + "-" + uuid.uuid4().hex[:6]
    )
    db.add(org)
    await db.flush()

    user = User(
        email=email,
        password_hash=hash_password(password),
        full_name=full_name,
        org_id=org.id,
        role="owner",
    )
    db.add(user)
    await db.commit()
    await db.refresh(org)
    await db.refresh(user)
    return org, user


async def authenticate_user(db: AsyncSession, email: str, password: str) -> User | None:
    result = await db.execute(
        select(User).where(User.email == email, User.is_active.is_(True))
    )
    user = result.scalar_one_or_none()
    if not user or not verify_password(password, user.password_hash):
        return None
    return user


async def create_invite(
    db: AsyncSession,
    org_id: uuid.UUID,
    email: str,
    role: str,
    invited_by: uuid.UUID,
) -> Invite:
    token = uuid.uuid4().hex
    invite = Invite(
        org_id=org_id,
        email=email,
        role=role,
        token=token,
        invited_by=invited_by,
        expires_at=datetime.now(timezone.utc)
        + timedelta(days=settings.invite_expire_days),
    )
    db.add(invite)
    await db.commit()
    await db.refresh(invite)
    return invite


async def accept_invite(
    db: AsyncSession,
    token: str,
    full_name: str,
    password: str,
) -> tuple[User, Invite]:
    result = await db.execute(
        select(Invite).where(Invite.token == token, Invite.accepted_at.is_(None))
    )
    invite = result.scalar_one_or_none()
    if not invite:
        raise ValueError("Invalid or expired invite")
    if invite.expires_at < datetime.now(timezone.utc):
        raise ValueError("Invite has expired")

    # Check if email already registered
    existing = await db.execute(select(User).where(User.email == invite.email))
    if existing.scalar_one_or_none():
        raise ValueError("Email already registered")

    user = User(
        email=invite.email,
        password_hash=hash_password(password),
        full_name=full_name,
        org_id=invite.org_id,
        role=invite.role,
    )
    db.add(user)
    invite.accepted_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(user)
    return user, invite
