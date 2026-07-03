import logging
from typing import AsyncGenerator

from fastapi import Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.APP_ENV == "development",
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db_session(request: Request) -> AsyncGenerator[AsyncSession, None]:
    tenant_id = getattr(request.state, "tenant_id", None)
    async with AsyncSessionLocal() as session:
        async with session.begin():
            if tenant_id:
                # SET LOCAL: scoped ke transaction ini — aman dengan connection pooling
                await session.execute(
                    text("SET LOCAL app.current_tenant_id = :tid"),
                    {"tid": str(tenant_id)},
                )
            yield session
