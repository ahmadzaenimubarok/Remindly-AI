import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.models.tenant import Tenant
from app.schemas.base import APIResponse
from app.schemas.billing import (
    BillingStatusResponse,
    CheckoutSessionResponse,
    CreateCheckoutSessionRequest,
)
from app.services.billing_service import create_checkout_session, handle_stripe_webhook

logger = logging.getLogger(__name__)

router = APIRouter(tags=["billing"])


@router.get("/api/v1/billing/status", response_model=APIResponse[BillingStatusResponse])
async def get_billing_status(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    tenant_id: str = request.state.tenant_id
    result = await db.execute(select(Tenant).where(Tenant.id == uuid.UUID(tenant_id)))
    tenant = result.scalar_one_or_none()
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant tidak ditemukan.")
    return APIResponse(data=BillingStatusResponse(
        plan=tenant.plan,
        plan_expires_at=tenant.plan_expires_at,
        stripe_customer_id=tenant.stripe_customer_id,
        pending_plan=tenant.pending_plan,
        pending_plan_date=tenant.pending_plan_date,
    ))


@router.post("/api/v1/billing/checkout", response_model=APIResponse[CheckoutSessionResponse])
async def create_checkout(
    body: CreateCheckoutSessionRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    tenant_id: str = request.state.tenant_id
    try:
        url = await create_checkout_session(
            tenant_id=tenant_id,
            plan=body.plan,
            success_url=body.success_url,
            cancel_url=body.cancel_url,
            db=db,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    # "modified" = subscription langsung diubah, tidak perlu redirect Stripe
    if url == "modified":
        return APIResponse(
            data=CheckoutSessionResponse(checkout_url="", modified=True),
            message="Plan berhasil diubah.",
        )
    return APIResponse(
        data=CheckoutSessionResponse(checkout_url=url),
        message="Checkout session berhasil dibuat.",
    )


@router.post("/webhooks/stripe")
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")
    try:
        await handle_stripe_webhook(payload, sig_header, db)
    except ValueError as e:
        logger.warning("Stripe webhook rejected", extra={"reason": str(e)})
        raise HTTPException(status_code=400, detail=str(e))
    return JSONResponse({"received": True})
