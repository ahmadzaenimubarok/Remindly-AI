import logging

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.feature_flags import check_feature_status
from app.schemas.base import APIResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/features", tags=["features"])


@router.get("/{feature_name}")
async def get_feature_status(
    feature_name: str,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> APIResponse[dict]:
    tenant_id: str = request.state.tenant_id
    status = await check_feature_status(tenant_id, feature_name, db)
    return APIResponse(data={"status": status.value})
