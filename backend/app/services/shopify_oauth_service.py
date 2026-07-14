import logging
import uuid

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import encrypt_credential
from app.models.tenant_credential import TenantCredential

logger = logging.getLogger(__name__)

SHOPIFY_API_VERSION = "2024-01"


async def exchange_code_for_token(shop_domain: str, code: str) -> dict | None:
    """Tukar authorization code → access token."""
    settings = get_settings()
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"https://{shop_domain}/admin/oauth/access_token",
                json={
                    "client_id": settings.SHOPIFY_API_KEY,
                    "client_secret": settings.SHOPIFY_API_SECRET,
                    "code": code,
                },
            )
            if response.is_success:
                return response.json()
            logger.error(
                f"exchange_code_for_token failed: {response.status_code} {response.text}"
            )
    except Exception:
        logger.exception("exchange_code_for_token error")
    return None


async def get_shop_info(shop_domain: str, access_token: str) -> dict | None:
    """Ambil informasi toko dari Shopify."""
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(
                f"https://{shop_domain}/admin/api/{SHOPIFY_API_VERSION}/shop.json",
                headers={"X-Shopify-Access-Token": access_token},
            )
            if response.is_success:
                return response.json().get("shop")
            logger.error(f"get_shop_info failed: {response.status_code} {response.text}")
    except Exception:
        logger.exception("get_shop_info error")
    return None


async def save_shopify_connection(
    tenant_id: str,
    shop_domain: str,
    access_token: str,
    shop_name: str,
    db: AsyncSession,
) -> TenantCredential:
    """Simpan atau update koneksi Shopify untuk tenant."""
    existing_result = await db.execute(
        select(TenantCredential).where(
            TenantCredential.tenant_id == uuid.UUID(tenant_id),
            TenantCredential.platform == "shopify",
        )
    )
    credential = existing_result.scalar_one_or_none()
    encrypted = encrypt_credential(access_token)

    if credential is None:
        credential = TenantCredential(
            tenant_id=uuid.UUID(tenant_id),
            platform="shopify",
            access_token_encrypted=encrypted,
            facebook_user_id=shop_domain,  # Reusing field for shop_domain
            page_id=shop_name,  # Reusing field for shop_name
        )
        db.add(credential)
    else:
        credential.access_token_encrypted = encrypted
        credential.facebook_user_id = shop_domain
        credential.page_id = shop_name

    await db.flush()
    logger.info(
        "Shopify connection saved",
        extra={"tenant_id": tenant_id, "shop_domain": shop_domain, "shop_name": shop_name},
    )
    return credential


async def get_shopify_credentials(tenant_id: str, db: AsyncSession) -> dict | None:
    """Ambil kredensial Shopify untuk tenant."""
    result = await db.execute(
        select(TenantCredential).where(
            TenantCredential.tenant_id == uuid.UUID(tenant_id),
            TenantCredential.platform == "shopify",
        )
    )
    credential = result.scalar_one_or_none()
    if credential is None:
        return None

    from app.core.security import decrypt_credential

    return {
        "shop_domain": credential.facebook_user_id,
        "shop_name": credential.page_id,
        "access_token": decrypt_credential(credential.access_token_encrypted),
    }


async def disconnect_shopify_connection(tenant_id: str, db: AsyncSession) -> None:
    """Hapus koneksi Shopify untuk tenant."""
    await db.execute(
        select(TenantCredential).where(
            TenantCredential.tenant_id == uuid.UUID(tenant_id),
            TenantCredential.platform == "shopify",
        )
    )
    # Delete the credential
    from sqlalchemy import delete

    await db.execute(
        delete(TenantCredential).where(
            TenantCredential.tenant_id == uuid.UUID(tenant_id),
            TenantCredential.platform == "shopify",
        )
    )
    await db.flush()
    logger.info("Shopify connection disconnected", extra={"tenant_id": tenant_id})
