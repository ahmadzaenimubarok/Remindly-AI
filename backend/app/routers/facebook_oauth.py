import base64
import json
import logging
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db_session
from app.schemas.facebook_oauth import FacebookConnectRequest
from app.services.facebook_oauth_service import (
    disconnect_facebook_connection,
    exchange_code_for_token,
    exchange_to_long_lived_token,
    get_facebook_user_id,
    get_user_pages,
    save_facebook_connection,
    subscribe_page_to_webhook,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth/facebook", tags=["facebook-oauth"])


@router.get("/login")
async def facebook_login(request: Request):
    """Generate Facebook OAuth URL untuk redirect customer."""
    settings = get_settings()
    tenant_id: str = request.state.tenant_id

    params = {
        "client_id": settings.META_APP_ID,
        "redirect_uri": settings.META_REDIRECT_URI,
        "scope": "pages_show_list,pages_messaging,pages_read_engagement,pages_manage_metadata",
        "response_type": "code",
        "state": tenant_id,
    }
    url = f"https://www.facebook.com/v21.0/dialog/oauth?{urlencode(params)}"
    return {"url": url}


@router.get("/callback")
async def facebook_callback(
    code: str | None = Query(None),
    state: str = Query(...),
    error: str | None = Query(None),
):
    """
    Backend callback endpoint — dipanggil oleh Facebook setelah user authorize.
    Exchange code → token → ambil pages → redirect ke frontend.
    """
    settings = get_settings()

    # Jika ada error dari Facebook
    if error:
        frontend_url = f"{settings.FRONTEND_URL}/auth/facebook/callback?error={error}"
        return RedirectResponse(url=frontend_url)

    # Jika tidak ada code
    if not code:
        error_msg = "no_code"
        frontend_url = f"{settings.FRONTEND_URL}/auth/facebook/callback?error={error_msg}"
        return RedirectResponse(url=frontend_url)

    # 1. Tukar code → short-lived token
    short_token_data = await exchange_code_for_token(code)
    if not short_token_data:
        error_msg = "exchange_failed"
        frontend_url = f"{settings.FRONTEND_URL}/auth/facebook/callback?error={error_msg}"
        return RedirectResponse(url=frontend_url)

    # 2. Tukar → long-lived token
    long_token_data = await exchange_to_long_lived_token(short_token_data["access_token"])
    if not long_token_data:
        error_msg = "long_lived_exchange_failed"
        frontend_url = f"{settings.FRONTEND_URL}/auth/facebook/callback?error={error_msg}"
        return RedirectResponse(url=frontend_url)

    long_token = long_token_data["access_token"]

    # 3. Ambil Facebook User ID
    user_id = await get_facebook_user_id(long_token)

    # 4. Ambil daftar Pages
    pages = await get_user_pages(long_token)

    # 5. Encode data dan redirect ke frontend
    callback_data = {
        "state": state,
        "facebook_user_id": user_id,
        "pages": [
            {
                "page_id": page["id"],
                "page_name": page["name"],
                "access_token": page["access_token"],
            }
            for page in pages
        ],
    }

    # Base64 encode data untuk passing ke frontend
    encoded_data = base64.urlsafe_b64encode(json.dumps(callback_data).encode()).decode()
    frontend_url = f"{settings.FRONTEND_URL}/auth/facebook/callback?data={encoded_data}"

    return RedirectResponse(url=frontend_url)


@router.post("/connect")
async def facebook_connect(
    body: FacebookConnectRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """Simpan koneksi Facebook Page ke tenant."""
    tenant_id: str = request.state.tenant_id

    # Simpan koneksi
    await save_facebook_connection(
        tenant_id=tenant_id,
        user_id="",
        page_id=body.page_id,
        page_token=body.access_token,
        db=db,
    )

    # Subscribe ke webhook
    subscribed = await subscribe_page_to_webhook(body.page_id, body.access_token)
    if not subscribed:
        logger.warning(
            "Failed to subscribe page to webhook",
            extra={"tenant_id": tenant_id, "page_id": body.page_id},
        )

    return {
        "message": "Facebook Page berhasil dihubungkan.",
        "page_id": body.page_id,
        "webhook_subscribed": subscribed,
    }


@router.delete("/disconnect")
async def facebook_disconnect(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """Hapus koneksi Facebook untuk tenant."""
    tenant_id: str = request.state.tenant_id
    await disconnect_facebook_connection(tenant_id, db)

    return {"message": "Facebook connection berhasil dihapus."}
