import logging
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import encrypt_credential
from app.models.product import Product
from app.models.tenant_credential import TenantCredential

logger = logging.getLogger(__name__)


async def get_settings_status(tenant_id: str, db: AsyncSession) -> dict:
    fb_result = await db.execute(
        select(TenantCredential).where(
            TenantCredential.tenant_id == uuid.UUID(tenant_id),
            TenantCredential.platform == "facebook",
        )
    )
    fb_cred = fb_result.scalar_one_or_none()
    facebook_connected = fb_cred is not None and not fb_cred.is_expired()

    ig_result = await db.execute(
        select(TenantCredential).where(
            TenantCredential.tenant_id == uuid.UUID(tenant_id),
            TenantCredential.platform == "instagram",
        )
    )
    ig_cred = ig_result.scalar_one_or_none()
    instagram_connected = ig_cred is not None and not ig_cred.is_expired()

    shopify_result = await db.execute(
        select(TenantCredential).where(
            TenantCredential.tenant_id == uuid.UUID(tenant_id),
            TenantCredential.platform == "shopify",
        )
    )
    shopify_cred = shopify_result.scalar_one_or_none()
    shopify_connected = shopify_cred is not None

    count_result = await db.execute(
        select(func.count()).select_from(Product).where(
            Product.tenant_id == uuid.UUID(tenant_id),
            Product.status == "active",
        )
    )
    product_count = count_result.scalar() or 0

    return {
        "facebook_connected": facebook_connected,
        "instagram_connected": instagram_connected,
        "shopify_connected": shopify_connected,
        "product_count": product_count,
    }


async def save_fb_token(
    tenant_id: str, page_token: str, page_id: str, db: AsyncSession
) -> TenantCredential:
    existing_result = await db.execute(
        select(TenantCredential).where(
            TenantCredential.tenant_id == uuid.UUID(tenant_id),
            TenantCredential.platform == "facebook",
        )
    )
    credential = existing_result.scalar_one_or_none()
    encrypted = encrypt_credential(page_token)

    if credential is None:
        credential = TenantCredential(
            tenant_id=uuid.UUID(tenant_id),
            platform="facebook",
            access_token_encrypted=encrypted,
        )
        db.add(credential)
    else:
        credential.access_token_encrypted = encrypted

    await db.flush()
    logger.info("FB token saved", extra={"tenant_id": tenant_id, "page_id": page_id})
    return credential


async def save_ig_token(
    tenant_id: str, page_token: str, account_id: str, db: AsyncSession
) -> TenantCredential:
    existing_result = await db.execute(
        select(TenantCredential).where(
            TenantCredential.tenant_id == uuid.UUID(tenant_id),
            TenantCredential.platform == "instagram",
        )
    )
    credential = existing_result.scalar_one_or_none()
    encrypted = encrypt_credential(page_token)

    if credential is None:
        credential = TenantCredential(
            tenant_id=uuid.UUID(tenant_id),
            platform="instagram",
            access_token_encrypted=encrypted,
        )
        db.add(credential)
    else:
        credential.access_token_encrypted = encrypted

    await db.flush()
    logger.info("IG token saved", extra={"tenant_id": tenant_id, "account_id": account_id})
    return credential
