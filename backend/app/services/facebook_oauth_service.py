import logging
from datetime import datetime, timedelta, timezone

import httpx

from app.core.config import get_settings
from app.core.security import encrypt_credential
from app.models.tenant_credential import TenantCredential

logger = logging.getLogger(__name__)

GRAPH_API_BASE = "https://graph.facebook.com/v21.0"
TOKEN_URL = f"{GRAPH_API_BASE}/oauth/access_token"
PAGES_URL = f"{GRAPH_API_BASE}/me/accounts"
SUBSCRIBE_URL = f"{GRAPH_API_BASE}/{{page_id}}/subscribed_apps"
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
                    "redirect_uri": settings.META_REDIRECT_URI,
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
                f"exchange_to_long_lived_token failed: {response.status_code} {response.text}"
            )
    except Exception:
        logger.exception("exchange_to_long_lived_token error")
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
            logger.error(f"get_user_pages failed: {response.status_code} {response.text}")
    except Exception:
        logger.exception("get_user_pages error")
    return []


async def subscribe_page_to_webhook(page_id: str, page_token: str) -> bool:
    """Subscribe Page ke aplikasi agar menerima webhook events."""
    url = SUBSCRIBE_URL.format(page_id=page_id)
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                url,
                params={"access_token": page_token},
                json={
                    "subscribed_fields": [
                        "messages",
                        "messaging_postbacks",
                        "feed",
                    ],
                },
            )
            if response.is_success:
                logger.info("Page subscribed to webhook", extra={"page_id": page_id})
                return True
            logger.error(
                f"subscribe_page_to_webhook failed: {response.status_code} {response.text}"
            )
    except Exception:
        logger.exception("subscribe_page_to_webhook error")
    return False


async def get_facebook_user_id(long_token: str) -> str | None:
    """Ambil Facebook User ID dari token."""
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(
                USER_URL,
                params={"access_token": long_token, "fields": "id"},
            )
            if response.is_success:
                return response.json().get("id")
            logger.error(
                f"get_facebook_user_id failed: {response.status_code} {response.text}"
            )
    except Exception:
        logger.exception("get_facebook_user_id error")
    return None


async def save_facebook_connection(
    tenant_id: str,
    user_id: str,
    page_id: str,
    page_token: str,
    db,
) -> TenantCredential:
    """Simpan atau update koneksi Facebook untuk tenant."""
    import uuid

    from sqlalchemy import select

    existing_result = await db.execute(
        select(TenantCredential).where(
            TenantCredential.tenant_id == uuid.UUID(tenant_id),
            TenantCredential.platform == "facebook",
            TenantCredential.page_id == page_id,
        )
    )
    credential = existing_result.scalar_one_or_none()
    encrypted = encrypt_credential(page_token)

    # Hitung expires_at (60 hari dari sekarang untuk long-lived token)
    expires_at = datetime.now(timezone.utc) + timedelta(days=60)

    if credential is None:
        credential = TenantCredential(
            tenant_id=uuid.UUID(tenant_id),
            platform="facebook",
            access_token_encrypted=encrypted,
            facebook_user_id=user_id,
            page_id=page_id,
            expires_at=expires_at,
        )
        db.add(credential)
    else:
        credential.access_token_encrypted = encrypted
        credential.facebook_user_id = user_id
        credential.page_id = page_id
        credential.expires_at = expires_at

    await db.flush()
    logger.info(
        "Facebook connection saved",
        extra={"tenant_id": tenant_id, "page_id": page_id, "user_id": user_id},
    )
    return credential


async def disconnect_facebook_connection(tenant_id: str, db) -> None:
    """Hapus semua koneksi Facebook untuk tenant."""
    import uuid

    from sqlalchemy import delete

    await db.execute(
        delete(TenantCredential).where(
            TenantCredential.tenant_id == uuid.UUID(tenant_id),
            TenantCredential.platform == "facebook",
        )
    )
    await db.flush()
    logger.info("Facebook connection disconnected", extra={"tenant_id": tenant_id})
