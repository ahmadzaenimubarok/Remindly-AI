import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db_session
from app.core.security import decode_token
from app.schemas.auth import LoginRequest, MeResponse, RegisterRequest, TokenResponse
from app.schemas.base import APIResponse
from app.schemas.tenant import TenantResponse
from app.services.auth_service import login_user, refresh_access_token, register_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def _set_auth_cookies(response: JSONResponse, access_token: str, refresh_token: str) -> None:
    settings = get_settings()
    is_prod = settings.APP_ENV == "production"
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        samesite="lax",
        secure=is_prod,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        samesite="lax",
        secure=is_prod,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        path="/",
    )


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


@router.post("/login")
async def login(
    body: LoginRequest,
    db: AsyncSession = Depends(get_db_session),
):
    tokens = await login_user(body, db)
    response = JSONResponse(
        content={"success": True, "data": {"token_type": "bearer"}, "message": None, "code": None}
    )
    _set_auth_cookies(response, tokens.access_token, tokens.refresh_token)
    return response


@router.post("/refresh")
async def refresh(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token tidak ditemukan.")
    tokens = await refresh_access_token(refresh_token, db)
    response = JSONResponse(
        content={"success": True, "data": {"token_type": "bearer"}, "message": None, "code": None}
    )
    _set_auth_cookies(response, tokens.access_token, tokens.refresh_token)
    return response


@router.post("/logout")
async def logout():
    response = JSONResponse(
        content={"success": True, "data": None, "message": "Logout berhasil.", "code": None}
    )
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")
    return response


@router.get("/me", response_model=APIResponse[MeResponse])
async def me(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Token tidak ditemukan.")
    try:
        payload = decode_token(token)
    except JWTError:
        raise HTTPException(status_code=401, detail="Token tidak valid.")
    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Tipe token tidak valid.")
    return APIResponse(data=MeResponse(
        user_id=payload["sub"],
        tenant_id=payload["tenant_id"],
        role=payload.get("role", "tenant_user"),
    ))
