import base64
import json
import logging
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db_session
from app.schemas.shopify import ShopifyConnectRequest
from app.services.shopify_oauth_service import (
    disconnect_shopify_connection,
    exchange_code_for_token,
    get_shop_info,
    save_shopify_connection,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth/shopify", tags=["shopify-oauth"])


@router.get("/login")
async def shopify_login(request: Request, shop: str):
    """Generate Shopify OAuth URL untuk redirect customer."""
    settings = get_settings()
    tenant_id: str = request.state.tenant_id

    # Pastikan format: my-store.myshopify.com (bukan my-store.myshopify.com.myshopify.com)
    shop_domain = shop.strip().lower()
    if not shop_domain.endswith(".myshopify.com"):
        shop_domain = f"{shop_domain}.myshopify.com"

    params = {
        "client_id": settings.SHOPIFY_API_KEY,
        "scope": "read_products,read_inventory",
        "redirect_uri": settings.SHOPIFY_REDIRECT_URI,
        "state": tenant_id,
    }
    url = f"https://{shop_domain}/admin/oauth/authorize?{urlencode(params)}"
    return {"url": url}


@router.get("/callback")
async def shopify_callback(
    code: str | None = Query(None),
    state: str = Query(...),
    shop: str = Query(...),
    error: str | None = Query(None),
):
    """
    Backend callback endpoint — dipanggil oleh Shopify setelah user authorize.
    Exchange code → token → ambil shop info → redirect ke frontend.
    """
    settings = get_settings()

    # Jika ada error dari Shopify
    if error:
        frontend_url = f"{settings.FRONTEND_URL}/auth/shopify/callback?error={error}"
        return RedirectResponse(url=frontend_url)

    # Jika tidak ada code
    if not code:
        error_msg = "no_code"
        frontend_url = f"{settings.FRONTEND_URL}/auth/shopify/callback?error={error_msg}"
        return RedirectResponse(url=frontend_url)

    # 1. Tukar code → access token
    token_data = await exchange_code_for_token(shop, code)
    if not token_data:
        error_msg = "exchange_failed"
        frontend_url = f"{settings.FRONTEND_URL}/auth/shopify/callback?error={error_msg}"
        return RedirectResponse(url=frontend_url)

    access_token = token_data.get("access_token")

    # 2. Ambil info toko
    shop_info = await get_shop_info(shop, access_token)
    shop_name = shop_info.get("name", shop) if shop_info else shop

    # 3. Encode data dan redirect ke frontend
    callback_data = {
        "state": state,
        "shop_domain": shop,
        "shop_name": shop_name,
        "access_token": access_token,
    }

    # Base64 encode data untuk passing ke frontend
    encoded_data = base64.urlsafe_b64encode(json.dumps(callback_data).encode()).decode()
    frontend_url = f"{settings.FRONTEND_URL}/auth/shopify/callback?data={encoded_data}"

    return RedirectResponse(url=frontend_url)


@router.post("/connect")
async def shopify_connect(
    body: ShopifyConnectRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """Simpan koneksi Shopify ke tenant."""
    tenant_id: str = request.state.tenant_id

    # Simpan koneksi
    await save_shopify_connection(
        tenant_id=tenant_id,
        shop_domain=body.shop_domain,
        access_token=body.access_token,
        shop_name=body.shop_name,
        db=db,
    )

    return {
        "message": "Shopify store berhasil dihubungkan.",
        "shop_domain": body.shop_domain,
        "shop_name": body.shop_name,
    }


@router.delete("/disconnect")
async def shopify_disconnect(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """Hapus koneksi Shopify untuk tenant."""
    tenant_id: str = request.state.tenant_id
    await disconnect_shopify_connection(tenant_id, db)

    return {"message": "Shopify connection berhasil dihapus."}
