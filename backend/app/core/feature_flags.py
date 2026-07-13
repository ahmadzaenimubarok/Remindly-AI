import logging
import uuid
from enum import Enum

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import Tenant
from app.models.tenant_credential import TenantCredential

logger = logging.getLogger(__name__)


class FeatureStatus(str, Enum):
    ACTIVE = "active"
    NOT_CONFIGURED = "not_configured"
    EXPIRED = "expired"
    PLAN_LOCKED = "plan_locked"
    QUOTA_EXCEEDED = "quota_exceeded"
    DISABLED_BY_USER = "disabled_by_user"


PLAN_FEATURES: dict[str, list[str]] = {
    "free": ["instagram_reply", "facebook_reply"],
    "starter": ["instagram_reply", "facebook_reply", "content_publish"],
    "pro": [
        "instagram_reply",
        "facebook_reply",
        "content_publish",
        "product_discovery",
        "sales_conversion",
        "analytics",
        "lead_classification",
        "shopify_import",
    ],
    "enterprise": ["*"],
}

# Fitur yang tidak butuh credential platform
CREDENTIAL_FREE_FEATURES = {"analytics", "product_discovery", "lead_classification"}


async def _get_tenant(tenant_id: str, db: AsyncSession) -> Tenant | None:
    result = await db.execute(select(Tenant).where(Tenant.id == uuid.UUID(tenant_id)))
    return result.scalar_one_or_none()


async def _is_quota_exceeded(tenant_id: str, feature: str, db: AsyncSession) -> bool:
    # Implementasi penuh di Fase 5 (usage metering)
    return False


async def _get_credential(
    tenant_id: str, feature: str, db: AsyncSession
) -> TenantCredential | None:
    platform = feature.split("_")[0]
    result = await db.execute(
        select(TenantCredential).where(
            TenantCredential.tenant_id == uuid.UUID(tenant_id),
            TenantCredential.platform == platform,
        )
    )
    return result.scalar_one_or_none()


async def check_feature_status(
    tenant_id: str,
    feature: str,
    db: AsyncSession,
) -> FeatureStatus:
    try:
        tenant = await _get_tenant(tenant_id, db)
        if tenant is None:
            return FeatureStatus.NOT_CONFIGURED

        plan_features = PLAN_FEATURES.get(tenant.plan, [])
        if "*" not in plan_features and feature not in plan_features:
            return FeatureStatus.PLAN_LOCKED

        if await _is_quota_exceeded(tenant_id, feature, db):
            return FeatureStatus.QUOTA_EXCEEDED

        if feature in CREDENTIAL_FREE_FEATURES:
            return FeatureStatus.ACTIVE

        credential = await _get_credential(tenant_id, feature, db)
        if credential is None:
            return FeatureStatus.NOT_CONFIGURED
        if credential.is_expired():
            return FeatureStatus.EXPIRED

        return FeatureStatus.ACTIVE

    except Exception:
        logger.exception(
            "check_feature_status error",
            extra={"tenant_id": tenant_id, "feature": feature},
        )
        return FeatureStatus.NOT_CONFIGURED  # safe default


async def log_skip(tenant_id: str, feature: str, status: FeatureStatus) -> None:
    logger.info(
        "Feature skipped",
        extra={"tenant_id": tenant_id, "feature": feature, "status": status.value},
    )
