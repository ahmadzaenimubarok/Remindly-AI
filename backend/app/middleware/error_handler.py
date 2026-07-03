import logging

from fastapi import Request
from fastapi.responses import JSONResponse

logger = logging.getLogger("internal")


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error(
        "Unhandled exception",
        extra={
            "path": str(request.url),
            "method": request.method,
            "tenant_id": getattr(request.state, "tenant_id", None),
            "error_type": type(exc).__name__,
        },
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "data": None,
            "message": "Terjadi kesalahan sistem. Tim kami sedang menangani ini.",
            "code": "INTERNAL_ERROR",
        },
    )


async def not_found_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content={
            "success": False,
            "data": None,
            "message": "Resource tidak ditemukan.",
            "code": "NOT_FOUND",
        },
    )


async def validation_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    from fastapi.exceptions import RequestValidationError
    errors = exc.errors() if isinstance(exc, RequestValidationError) else []
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "data": None,
            "message": "Data yang dikirim tidak valid.",
            "code": "VALIDATION_ERROR",
            "errors": [
                {"field": ".".join(str(loc) for loc in e["loc"]), "msg": e["msg"]}
                for e in errors
            ],
        },
    )
