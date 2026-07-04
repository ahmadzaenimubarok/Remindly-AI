import logging
import uuid

from fastapi import HTTPException
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.tenant import Tenant
from app.models.user import User
from dataclasses import dataclass

from app.schemas.auth import LoginRequest, RegisterRequest  # noqa: F401
from app.services.tenant_service import provision_tenant

logger = logging.getLogger(__name__)


@dataclass
class TokenPair:
    access_token: str
    refresh_token: str


def _build_token_payload(user: User) -> dict:
    return {
        "sub": str(user.id),
        "tenant_id": str(user.tenant_id) if user.tenant_id else None,
        "role": user.role,
    }


def _make_token_pair(user: User) -> TokenPair:
    payload = _build_token_payload(user)
    return TokenPair(
        access_token=create_access_token(payload),
        refresh_token=create_refresh_token(payload),
    )


async def register_user(
    body: RegisterRequest, db: AsyncSession
) -> tuple[User, Tenant]:
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email sudah terdaftar.")

    tenant = await provision_tenant(name=body.name, email=body.email, db=db)

    user = User(
        tenant_id=tenant.id,
        email=body.email,
        password_hash=hash_password(body.password),
        role="tenant_user",
    )
    db.add(user)
    await db.flush()

    logger.info(
        "User registered",
        extra={"user_id": str(user.id), "tenant_id": str(tenant.id)},
    )
    return user, tenant


async def login_user(body: LoginRequest, db: AsyncSession) -> TokenPair:
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Email atau password salah.")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Akun dinonaktifkan.")

    logger.info("User logged in", extra={"user_id": str(user.id)})
    return _make_token_pair(user)


async def refresh_access_token(
    refresh_token: str, db: AsyncSession
) -> TokenPair:
    try:
        payload = decode_token(refresh_token)
    except JWTError:
        raise HTTPException(status_code=401, detail="Refresh token tidak valid.")

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Bukan refresh token.")

    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User tidak ditemukan atau nonaktif.")

    return _make_token_pair(user)
