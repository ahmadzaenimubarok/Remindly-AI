import logging
import uuid
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import select

from app.core.config import get_settings
from app.core.security import encrypt_credential
from app.models.tenant_credential import TenantCredential

logger = logging.getLogger(__name__)

GRAPH_API_BASE = "https://graph.facebook.com/v21.0"
TOKEN_URL = f"{GRAPH_API_BASE}/oauth/access_token"
PAGES_URL = f"{GRAPH_API_BASE}/me/accounts"
USER_URL = f"{GRAPH_API_BASE}/me"


async def exchange_code_for_token(code: str) -> dict | None:
    """Tukar authorization code → short-lived access token."""
    settings = get_settings()
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(
                TOKEN_URL,
                params={
                    "client_id": settings.META_APP_ID,
                    "client_secret": settings.META_APP_SECRET,
                    "redirect_uri": settings.META_IG_REDIRECT_URI,
                    "code": code,
                },
            )
            if response.is_success:
                return response.json()
            logger.error(
                f"IG exchange_code_for_token failed: {response.status_code} {response.text}"
            )
    except Exception:
        logger.exception("IG exchange_code_for_token error")
    return None


async def exchange_to_long_lived_token(short_token: str) -> dict | None:
    """Tukar short-lived token → long-lived token (60 hari)."""
    settings = get_settings()
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(
                TOKEN_URL,
                params={
                    "grant_type": "fb_exchange_token",
                    "client_id": settings.META_APP_ID,
                    "client_secret": settings.META_APP_SECRET,
                    "fb_exchange_token": short_token,
                },
            )
            if response.is_success:
                return response.json()
            logger.error(
                f"IG exchange_to_long_lived_token failed: {response.status_code} {response.text}"
            )
    except Exception:
        logger.exception("IG exchange_to_long_lived_token error")
    return None


async def get_user_pages(long_token: str) -> list[dict]:
    """Ambil daftar Facebook Pages yang dikelola user."""
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(
                PAGES_URL,
                params={"access_token": long_token},
            )
            if response.is_success:
                data = response.json()
                return data.get("data", [])
            logger.error(f"IG get_user_pages failed: {response.status_code} {response.text}")
    except Exception:
        logger.exception("IG get_user_pages error")
    return []


async def get_instagram_accounts_for_pages(
    long_token: str, pages: list[dict]
) -> list[dict]:
    """Untuk setiap Facebook Page, cek apakah punya Instagram Business Account.
    Kembalikan list page yang punya IG account beserta info IG-nya."""
    results = []
    try:
        with httpx.Client(timeout=30.0) as client:
            for page in pages:
                page_id = page["id"]
                try:
                    response = client.get(
                        f"{GRAPH_API_BASE}/{page_id}",
                        params={
                            "access_token": long_token,
                            "fields": "instagram_business_account{id,name,username}",
                        },
                    )
                    if response.is_success:
                        data = response.json()
                        ig_account = data.get("instagram_business_account")
                        if ig_account:
                            results.append(
                                {
                                    "page_id": page_id,
                                    "page_name": page["name"],
                                    "page_token": page["access_token"],
                                    "instagram_account_id": ig_account["id"],
                                    "instagram_username": ig_account.get("username", ""),
                                    "instagram_name": ig_account.get("name", ""),
                                }
                            )
                except Exception:
                    logger.warning(
                        "Failed to check IG account for page",
                        extra={"page_id": page_id},
                    )
    except Exception:
        logger.exception("get_instagram_accounts_for_pages error")
    return results


async def save_instagram_connection(
    tenant_id: str,
    page_id: str,
    page_token: str,
    ig_account_id: str,
    db,
) -> TenantCredential:
    """Simpan atau update koneksi Instagram untuk tenant."""
    existing_result = await db.execute(
        select(TenantCredential).where(
            TenantCredential.tenant_id == uuid.UUID(tenant_id),
            TenantCredential.platform == "instagram",
            TenantCredential.page_id == page_id,
        )
    )
    credential = existing_result.scalar_one_or_none()
    encrypted = encrypt_credential(page_token)

    expires_at = datetime.now(timezone.utc) + timedelta(days=60)

    if credential is None:
        credential = TenantCredential(
            tenant_id=uuid.UUID(tenant_id),
            platform="instagram",
            access_token_encrypted=encrypted,
            page_id=page_id,
            facebook_user_id=ig_account_id,
            expires_at=expires_at,
        )
        db.add(credential)
    else:
        credential.access_token_encrypted = encrypted
        credential.page_id = page_id
        credential.facebook_user_id = ig_account_id
        credential.expires_at = expires_at

    await db.flush()
    logger.info(
        "Instagram connection saved",
        extra={"tenant_id": tenant_id, "page_id": page_id, "ig_account_id": ig_account_id},
    )
    return credential


async def disconnect_instagram_connection(tenant_id: str, db) -> None:
    """Hapus semua koneksi Instagram untuk tenant."""
    from sqlalchemy import delete

    await db.execute(
        delete(TenantCredential).where(
            TenantCredential.tenant_id == uuid.UUID(tenant_id),
            TenantCredential.platform == "instagram",
        )
    )
    await db.flush()
    logger.info("Instagram connection disconnected", extra={"tenant_id": tenant_id})
