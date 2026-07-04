import logging

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from jose import JWTError
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.security import decode_token

logger = logging.getLogger(__name__)

PUBLIC_PATHS = {"/", "/health", "/docs", "/openapi.json", "/redoc"}
AUTH_PATHS = {"/api/v1/auth/register", "/api/v1/auth/login", "/api/v1/auth/refresh", "/api/v1/auth/logout", "/api/v1/auth/me"}
WEBHOOK_PATH_PREFIX = "/webhooks"


class TenantContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path

        if path in PUBLIC_PATHS or path in AUTH_PATHS or path.startswith(WEBHOOK_PATH_PREFIX):
            return await call_next(request)

        token = self._extract_token(request)
        if not token:
            return self._unauthorized("Token tidak ditemukan.")

        try:
            payload = decode_token(token)
        except JWTError:
            return self._unauthorized("Token tidak valid atau sudah kedaluwarsa.")

        if payload.get("type") != "access":
            return self._unauthorized("Tipe token tidak valid.")

        request.state.tenant_id = payload.get("tenant_id")
        request.state.user_id = payload.get("sub")
        request.state.role = payload.get("role", "tenant_user")

        return await call_next(request)

    def _extract_token(self, request: Request) -> str | None:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            return auth_header[7:]
        return None

    def _unauthorized(self, message: str) -> JSONResponse:
        return JSONResponse(
            status_code=401,
            content={
                "success": False,
                "data": None,
                "message": message,
                "code": "UNAUTHORIZED",
            },
        )
