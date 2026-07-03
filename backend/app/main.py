import logging

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from app.middleware.error_handler import (
    global_exception_handler,
    validation_exception_handler,
)
from app.middleware.rate_limiter import RateLimiterMiddleware
from app.middleware.tenant_context import TenantContextMiddleware
from app.routers import auth

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

app = FastAPI(
    title="Reseller AI",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Middleware (urutan: luar ke dalam)
app.add_middleware(RateLimiterMiddleware)
app.add_middleware(TenantContextMiddleware)

# Exception handlers
app.add_exception_handler(Exception, global_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)

# Routers
app.include_router(auth.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
