import hashlib
import hmac
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db_session
from app.models.tenant_credential import TenantCredential
from app.schemas.webhook import FacebookWebhookPayload
from workers.engagement_worker import process_facebook_event, process_instagram_event

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def _verify_fb_signature(body: bytes, signature_header: str | None, app_secret: str) -> bool:
    """Verifikasi X-Hub-Signature-256 dari Facebook."""
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    expected = "sha256=" + hmac.new(
        app_secret.encode(), body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature_header)


async def _get_tenant_id_by_page_id(page_id: str, db: AsyncSession) -> str | None:
    """Lookup tenant_id dari page_id yang ada di database."""
    result = await db.execute(
        select(TenantCredential.tenant_id).where(
            TenantCredential.platform == "facebook",
            TenantCredential.page_id == page_id,
        )
    )
    row = result.first()
    return str(row[0]) if row else None


async def _get_tenant_id_by_ig_account_id(account_id: str, db: AsyncSession) -> str | None:
    """Lookup tenant_id dari Instagram account_id (stored in facebook_user_id column)."""
    result = await db.execute(
        select(TenantCredential.tenant_id).where(
            TenantCredential.platform == "instagram",
            TenantCredential.facebook_user_id == account_id,
        )
    )
    row = result.first()
    return str(row[0]) if row else None


@router.get("/facebook", response_class=PlainTextResponse)
async def facebook_verify(
    hub_mode: str = Query(alias="hub.mode"),
    hub_verify_token: str = Query(alias="hub.verify_token"),
    hub_challenge: str = Query(alias="hub.challenge"),
) -> str:
    """Endpoint verifikasi webhook Facebook — dipanggil satu kali saat setup."""
    settings = get_settings()
    if hub_mode == "subscribe" and hub_verify_token == settings.META_VERIFY_TOKEN:
        logger.info("Facebook webhook verified")
        return hub_challenge
    raise HTTPException(status_code=403, detail="Verify token tidak valid.")


@router.post("/facebook")
async def facebook_receive(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Terima event webhook Facebook (komentar + Messenger DM)."""
    settings = get_settings()
    body = await request.body()

    if settings.META_APP_SECRET:
        signature = request.headers.get("X-Hub-Signature-256")
        if not _verify_fb_signature(body, signature, settings.META_APP_SECRET):
            logger.warning("Invalid Facebook webhook signature")
            raise HTTPException(status_code=403, detail="Signature tidak valid.")

    try:
        payload = FacebookWebhookPayload.model_validate_json(body)
    except Exception:
        raise HTTPException(status_code=400, detail="Payload tidak valid.")

    if payload.object != "page":
        return {"status": "ignored", "reason": "object bukan page"}

    queued = 0
    for entry in payload.entry:
        # Lookup tenant_id dari page_id
        page_id = str(entry.get("id", ""))
        tenant_id = await _get_tenant_id_by_page_id(page_id, db)

        if not tenant_id:
            logger.warning(
                "No tenant found for page_id",
                extra={"page_id": page_id},
            )
            continue

        # Komentar Facebook
        for change in entry.get("changes", []):
            if change.get("field") == "feed":
                value = change.get("value", {})
                if value.get("item") == "comment":
                    event = {
                        "channel_type": "comment",
                        "comment_id": value.get("comment_id", ""),
                        "message": value.get("message", ""),
                        "from_id": value.get("from", {}).get("id", ""),
                        "from_name": value.get("from", {}).get("name"),
                        "post_id": value.get("post_id", ""),
                    }
                    process_facebook_event.delay(tenant_id, event)
                    queued += 1

        # Messenger DM
        for msg_event in entry.get("messaging", []):
            if "message" in msg_event and not msg_event["message"].get("is_echo"):
                event = {
                    "channel_type": "dm",
                    "message_id": msg_event["message"].get("mid", ""),
                    "message": msg_event["message"].get("text", ""),
                    "sender_id": msg_event.get("sender", {}).get("id", ""),
                }
                process_facebook_event.delay(tenant_id, event)
                queued += 1

    logger.info("Facebook webhook received", extra={"queued": queued})
    return {"status": "ok", "queued": queued}


@router.get("/instagram", response_class=PlainTextResponse)
async def instagram_verify(
    hub_mode: str = Query(alias="hub.mode"),
    hub_verify_token: str = Query(alias="hub.verify_token"),
    hub_challenge: str = Query(alias="hub.challenge"),
) -> str:
    """Endpoint verifikasi webhook Instagram — dipanggil sekali saat setup di Meta Console."""
    settings = get_settings()
    if hub_mode == "subscribe" and hub_verify_token == settings.META_VERIFY_TOKEN:
        logger.info("Instagram webhook verified")
        return hub_challenge
    raise HTTPException(status_code=403, detail="Verify token tidak valid.")


@router.post("/instagram")
async def instagram_receive(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Terima event webhook Instagram (DM)."""
    settings = get_settings()
    body = await request.body()

    if settings.META_APP_SECRET:
        signature = request.headers.get("X-Hub-Signature-256")
        if not _verify_fb_signature(body, signature, settings.META_APP_SECRET):
            logger.warning("Invalid Instagram webhook signature")
            raise HTTPException(status_code=403, detail="Signature tidak valid.")

    try:
        payload = FacebookWebhookPayload.model_validate_json(body)
    except Exception:
        raise HTTPException(status_code=400, detail="Payload tidak valid.")

    if payload.object != "instagram":
        return {"status": "ignored", "reason": "object bukan instagram"}

    queued = 0
    for entry in payload.entry:
        account_id = str(entry.get("id", ""))
        tenant_id = await _get_tenant_id_by_ig_account_id(account_id, db)

        if not tenant_id:
            logger.warning(
                "No tenant found for Instagram account",
                extra={"account_id": account_id},
            )
            continue

        for msg_event in entry.get("messaging", []):
            if "message" in msg_event and not msg_event["message"].get("is_echo"):
                event = {
                    "channel_type": "dm",
                    "message_id": msg_event["message"].get("mid", ""),
                    "message": msg_event["message"].get("text", ""),
                    "sender_id": msg_event.get("sender", {}).get("id", ""),
                }
                process_instagram_event.delay(tenant_id, event)
                queued += 1

    logger.info("Instagram webhook received", extra={"queued": queued})
    return {"status": "ok", "queued": queued}
