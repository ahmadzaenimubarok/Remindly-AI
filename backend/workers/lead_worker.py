import asyncio
import logging

from workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="workers.lead_worker.classify_lead",
    queue="leads",
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def classify_lead(self, tenant_id: str, customer_id: str) -> None:
    """
    Klasifikasi / update tier lead berdasarkan conversation terbaru.
    Dipanggil setelah engagement_worker commit (transaction selesai).
    """
    async def _run() -> None:
        from sqlalchemy.pool import NullPool
        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
        from app.core.config import get_settings
        from app.core.feature_flags import FeatureStatus, check_feature_status
        from app.services.lead_service import upsert_lead

        import app.models  # noqa: F401 — register semua mapper

        _settings = get_settings()
        _engine = create_async_engine(_settings.DATABASE_URL, poolclass=NullPool)
        _Session = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)

        try:
            # check_feature_status pakai session sendiri (auto-begin internal)
            async with _Session() as session:
                status = await check_feature_status(tenant_id, "lead_classification", session)

            if status != FeatureStatus.ACTIVE:
                logger.info(
                    "lead_classification skipped",
                    extra={"tenant_id": tenant_id, "status": status.value},
                )
                return

            # upsert_lead pakai session baru dengan explicit transaction
            async with _Session() as session:
                async with session.begin():
                    await upsert_lead(tenant_id, customer_id, session)
        finally:
            await _engine.dispose()

    try:
        asyncio.run(_run())
        logger.info(
            "Lead classified",
            extra={"tenant_id": tenant_id, "customer_id": customer_id},
        )
    except Exception as exc:
        logger.error(
            "classify_lead failed",
            extra={"tenant_id": tenant_id, "customer_id": customer_id, "error": str(exc)},
        )
        raise


@celery_app.task(
    name="workers.lead_worker.decay_leads",
    queue="leads",
)
def decay_leads() -> None:
    """Celery Beat job — jalankan auto-decay tier lead setiap hari."""
    async def _run() -> None:
        from sqlalchemy.pool import NullPool
        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
        from app.core.config import get_settings
        from app.services.lead_service import run_decay

        _settings = get_settings()
        _engine = create_async_engine(_settings.DATABASE_URL, poolclass=NullPool)
        _Session = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)

        try:
            async with _Session() as session:
                async with session.begin():
                    count = await run_decay(session)
            logger.info("Lead decay completed", extra={"updated": count})
        finally:
            await _engine.dispose()

    try:
        asyncio.run(_run())
    except Exception as exc:
        logger.error("decay_leads failed", extra={"error": str(exc)})
        raise
