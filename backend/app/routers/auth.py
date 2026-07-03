import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.schemas.auth import LoginRequest, RefreshRequest, RegisterRequest, TokenResponse
from app.schemas.base import APIResponse
from app.schemas.tenant import TenantResponse
from app.services.auth_service import login_user, refresh_access_token, register_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/register", response_model=APIResponse[TenantResponse], status_code=201)
async def register(
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db_session),
):
    user, tenant = await register_user(body, db)
    return APIResponse(
        data=TenantResponse.model_validate(tenant),
        message="Akun berhasil dibuat. Selamat datang!",
    )


@router.post("/login", response_model=APIResponse[TokenResponse])
async def login(
    body: LoginRequest,
    db: AsyncSession = Depends(get_db_session),
):
    tokens = await login_user(body, db)
    return APIResponse(data=tokens)


@router.post("/refresh", response_model=APIResponse[TokenResponse])
async def refresh(
    body: RefreshRequest,
    db: AsyncSession = Depends(get_db_session),
):
    tokens = await refresh_access_token(body.refresh_token, db)
    return APIResponse(data=tokens)
