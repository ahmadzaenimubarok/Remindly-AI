import logging

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.schemas.base import APIResponse
from app.schemas.settings import SaveFBTokenRequest, SettingsResponse
from app.services.settings_service import get_settings_status, save_fb_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/settings", tags=["settings"])


@router.get("", response_model=APIResponse[SettingsResponse])
async def get_settings_endpoint(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    tenant_id: str = request.state.tenant_id
    status = await get_settings_status(tenant_id, db)
    return APIResponse(data=SettingsResponse(**status))


@router.post("/facebook-token", response_model=APIResponse[None])
async def save_facebook_token(
    body: SaveFBTokenRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    tenant_id: str = request.state.tenant_id
    await save_fb_token(tenant_id, body.page_token, body.page_id, db)
    return APIResponse(data=None, message="Facebook Page token berhasil disimpan.")
