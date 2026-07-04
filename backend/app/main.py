import logging

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.middleware.error_handler import (
    global_exception_handler,
    validation_exception_handler,
)
from app.middleware.rate_limiter import RateLimiterMiddleware
from app.middleware.tenant_context import TenantContextMiddleware
from app.routers import auth, conversations, features, webhooks

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

# Middleware (urutan: luar ke dalam — Starlette reverse-order, ditambah terakhir = dieksekusi pertama)
app.add_middleware(RateLimiterMiddleware)
app.add_middleware(TenantContextMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "https://dashboard.jawakoentji.my.id"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handlers
app.add_exception_handler(Exception, global_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)

# Routers
app.include_router(auth.router)
app.include_router(webhooks.router)
app.include_router(conversations.router)
app.include_router(features.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
