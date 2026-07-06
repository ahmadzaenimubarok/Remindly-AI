import asyncio
import logging

from workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="workers.engagement_worker.process_facebook_event",
    queue="engagement",
    max_retries=3,
    default_retry_delay=30,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def process_facebook_event(self, tenant_id: str, event: dict) -> None:
    """
    Proses satu event Facebook (komentar atau Messenger DM) untuk tenant.
    event["channel_type"]: "comment" | "dm"
    """
    channel_type = event.get("channel_type", "comment")

    async def _run() -> str | None:
        from sqlalchemy.pool import NullPool
        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
        from app.core.config import get_settings
        from app.services.engagement_service import (
            process_facebook_comment,
            process_messenger_message,
        )

        import app.models  # noqa: F401 — register semua mapper

        # NullPool: hindari reuse connection pool antar fork (asyncio loop berbeda)
        _settings = get_settings()
        _engine = create_async_engine(_settings.DATABASE_URL, poolclass=NullPool)
        _Session = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)

        customer_id: str | None = None
        try:
            async with _Session() as session:
                async with session.begin():
                    if channel_type == "comment":
                        customer_id = await process_facebook_comment(tenant_id, event, session)
                    elif channel_type == "dm":
                        customer_id = await process_messenger_message(tenant_id, event, session)
                    else:
                        logger.warning(
                            "Unknown channel_type",
                            extra={"channel_type": channel_type, "tenant_id": tenant_id},
                        )
            # classify_lead dipanggil SETELAH session.begin() selesai (commit sudah terjadi)
            return customer_id
        finally:
            await _engine.dispose()

    try:
        customer_id = asyncio.run(_run())
        logger.info(
            "Facebook event processed",
            extra={"tenant_id": tenant_id, "channel_type": channel_type},
        )
        if customer_id is not None:
            from workers.lead_worker import classify_lead
            classify_lead.delay(tenant_id, customer_id)
    except Exception as exc:
        logger.error(
            "process_facebook_event failed",
            extra={"tenant_id": tenant_id, "error": str(exc)},
        )
        raise


@celery_app.task(
    bind=True,
    name="workers.engagement_worker.process_instagram_event",
    queue="engagement",
    max_retries=3,
    default_retry_delay=30,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def process_instagram_event(self, tenant_id: str, event: dict) -> None:
    """
    Proses satu event Instagram DM untuk tenant.
    event["channel_type"]: "dm" (comment belum didukung)
    """
    channel_type = event.get("channel_type", "dm")

    async def _run() -> str | None:
        from sqlalchemy.pool import NullPool
        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
        from app.core.config import get_settings
        from app.services.engagement_service import process_instagram_dm

        import app.models  # noqa: F401

        _settings = get_settings()
        _engine = create_async_engine(_settings.DATABASE_URL, poolclass=NullPool)
        _Session = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)

        customer_id: str | None = None
        try:
            async with _Session() as session:
                async with session.begin():
                    if channel_type == "dm":
                        customer_id = await process_instagram_dm(tenant_id, event, session)
                    else:
                        logger.warning(
                            "Unsupported channel_type for Instagram",
                            extra={"channel_type": channel_type, "tenant_id": tenant_id},
                        )
            return customer_id
        finally:
            await _engine.dispose()

    try:
        customer_id = asyncio.run(_run())
        logger.info(
            "Instagram event processed",
            extra={"tenant_id": tenant_id, "channel_type": channel_type},
        )
        if customer_id is not None:
            from workers.lead_worker import classify_lead
            classify_lead.delay(tenant_id, customer_id)
    except Exception as exc:
        logger.error(
            "process_instagram_event failed",
            extra={"tenant_id": tenant_id, "error": str(exc)},
        )
        raise
