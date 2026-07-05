import logging
import uuid
from datetime import datetime, timedelta, timezone

import stripe
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.tenant import Tenant

logger = logging.getLogger(__name__)

PLAN_PRICES: dict[str, str] = {
    "starter": "price_REPLACE_WITH_STRIPE_PRICE_ID_STARTER",
    "pro": "price_REPLACE_WITH_STRIPE_PRICE_ID_PRO",
    "enterprise": "price_REPLACE_WITH_STRIPE_PRICE_ID_ENTERPRISE",
}

PLAN_DURATION_DAYS: dict[str, int] = {
    "starter": 30,
    "pro": 30,
    "enterprise": 365,
}


async def _get_tenant(tenant_id: str, db: AsyncSession) -> Tenant | None:
    result = await db.execute(select(Tenant).where(Tenant.id == uuid.UUID(tenant_id)))
    return result.scalar_one_or_none()


async def create_checkout_session(
    tenant_id: str,
    plan: str,
    success_url: str,
    cancel_url: str,
    db: AsyncSession,
) -> str:
    settings = get_settings()
    stripe.api_key = settings.STRIPE_SECRET_KEY

    tenant = await _get_tenant(tenant_id, db)
    if tenant is None:
        raise ValueError("Tenant tidak ditemukan")

    if plan not in PLAN_PRICES:
        raise ValueError(f"Plan tidak valid: {plan}")

    if tenant.stripe_customer_id:
        customer_id = tenant.stripe_customer_id
    else:
        customer = stripe.Customer.create(
            email=tenant.email,
            name=tenant.name,
            metadata={"tenant_id": tenant_id},
        )
        customer_id = customer.id
        tenant.stripe_customer_id = customer_id

    session = stripe.checkout.Session.create(
        customer=customer_id,
        payment_method_types=["card"],
        line_items=[{"price": PLAN_PRICES[plan], "quantity": 1}],
        mode="subscription",
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={"tenant_id": tenant_id, "plan": plan},
    )

    logger.info(
        "Stripe checkout session created",
        extra={"tenant_id": tenant_id, "plan": plan, "session_id": session.id},
    )
    return session.url


async def handle_stripe_webhook(
    payload: bytes,
    sig_header: str,
    db: AsyncSession,
) -> None:
    settings = get_settings()
    stripe.api_key = settings.STRIPE_SECRET_KEY

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except stripe.SignatureVerificationError:
        logger.warning("Stripe webhook signature invalid")
        raise ValueError("Signature tidak valid")

    if event["type"] != "checkout.session.completed":
        logger.debug("Stripe webhook ignored", extra={"event_type": event["type"]})
        return

    session_obj = event["data"]["object"]
    metadata = session_obj.get("metadata", {})
    tenant_id = metadata.get("tenant_id")
    plan = metadata.get("plan")
    customer_id = session_obj.get("customer")

    if not tenant_id or not plan:
        logger.error("Stripe webhook missing metadata", extra={"metadata": metadata})
        return

    tenant = await _get_tenant(tenant_id, db)
    if tenant is None:
        logger.error("Stripe webhook tenant not found", extra={"tenant_id": tenant_id})
        return

    duration = PLAN_DURATION_DAYS.get(plan, 30)
    expires_at = datetime.now(timezone.utc) + timedelta(days=duration)

    tenant.plan = plan
    tenant.plan_expires_at = expires_at.isoformat()
    if customer_id:
        tenant.stripe_customer_id = customer_id

    logger.info(
        "Tenant plan upgraded via Stripe",
        extra={"tenant_id": tenant_id, "plan": plan, "expires_at": expires_at.isoformat()},
    )
