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
    "starter": "price_1TpqHTQ6INtHNgjR1CMvPwSD",
    "pro": "price_1TpqHUQ6INtHNgjRXeuZFc2M",
    "enterprise": "price_1TpqHVQ6INtHNgjRfxnqLEqY",
}

PLAN_DURATION_DAYS: dict[str, int] = {
    "starter": 30,
    "pro": 30,
    "enterprise": 365,
}

PLAN_RANK: dict[str, int] = {"free": 0, "starter": 1, "pro": 2, "enterprise": 3}


async def _get_tenant(tenant_id: str, db: AsyncSession) -> Tenant | None:
    result = await db.execute(select(Tenant).where(Tenant.id == uuid.UUID(tenant_id)))
    return result.scalar_one_or_none()


async def _get_tenant_by_customer_id(customer_id: str, db: AsyncSession) -> Tenant | None:
    result = await db.execute(
        select(Tenant).where(Tenant.stripe_customer_id == customer_id)
    )
    return result.scalar_one_or_none()


def _is_upgrade(current_plan: str, new_plan: str) -> bool:
    return PLAN_RANK.get(new_plan, 0) > PLAN_RANK.get(current_plan, 0)


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

    # Blok hanya kalau plan sama DAN tidak ada pending downgrade yang perlu dibatalkan
    if plan == tenant.plan and not tenant.pending_plan:
        raise ValueError("Plan yang dipilih sama dengan plan aktif")
    # Juga blok kalau plan sama dengan pending (downgrade yang sama sudah dijadwalkan)
    if plan == tenant.pending_plan:
        raise ValueError("Downgrade ke plan ini sudah dijadwalkan")

    # Sudah punya subscription aktif → modifikasi langsung, tidak perlu Checkout
    if tenant.stripe_subscription_id:
        await _modify_subscription(tenant, plan, db)
        return "modified"

    # Belum punya subscription → buat via Checkout Session
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

    logger.info("Checkout session created", extra={"tenant_id": tenant_id, "plan": plan})
    return session.url


async def _modify_subscription(tenant: Tenant, new_plan: str, db: AsyncSession) -> None:
    """
    Upgrade              → proration_behavior='always_invoice': bayar selisih prorata langsung.
    Cancel pending        → kembalikan ke plan aktif, batalkan scheduled downgrade.
    Downgrade baru        → proration_behavior='none': pindah plan di renewal berikutnya.
    """
    settings = get_settings()
    stripe.api_key = settings.STRIPE_SECRET_KEY

    sub_obj = stripe.Subscription.retrieve(tenant.stripe_subscription_id)
    sub_dict = sub_obj.to_dict()
    item_id = sub_dict["items"]["data"][0]["id"]
    # current_period_end kosong di billing_mode=flexible — fallback ke billing_cycle_anchor + 1 bulan
    period_end_ts = sub_dict.get("current_period_end") or sub_dict.get("billing_cycle_anchor")

    # Batalkan pending downgrade — kembalikan ke plan aktif saat ini
    canceling_pending = tenant.pending_plan and new_plan == tenant.plan
    upgrading = _is_upgrade(tenant.plan, new_plan)

    if canceling_pending:
        # Kembalikan subscription ke price plan aktif, batalkan scheduled change
        stripe.Subscription.modify(
            tenant.stripe_subscription_id,
            items=[{"id": item_id, "price": PLAN_PRICES[tenant.plan]}],
            proration_behavior="none",
            billing_cycle_anchor="unchanged",
            metadata={"tenant_id": str(tenant.id), "plan": tenant.plan},
        )
        tenant.pending_plan = None
        tenant.pending_plan_date = None
        logger.info("Pending downgrade cancelled", extra={"tenant_id": str(tenant.id), "plan": tenant.plan})

    elif upgrading:
        stripe.Subscription.modify(
            tenant.stripe_subscription_id,
            items=[{"id": item_id, "price": PLAN_PRICES[new_plan]}],
            proration_behavior="always_invoice",
            metadata={"tenant_id": str(tenant.id), "plan": new_plan},
        )
        # Batalkan juga pending downgrade kalau ada
        tenant.pending_plan = None
        tenant.pending_plan_date = None
        logger.info("Subscription upgrade initiated", extra={"tenant_id": str(tenant.id), "plan": new_plan})

    else:
        # Downgrade baru: jadwalkan di akhir periode berjalan
        if not period_end_ts:
            raise ValueError("Tidak dapat membaca periode berlangganan dari Stripe")
        stripe.Subscription.modify(
            tenant.stripe_subscription_id,
            items=[{"id": item_id, "price": PLAN_PRICES[new_plan]}],
            proration_behavior="none",
            billing_cycle_anchor="unchanged",
            metadata={"tenant_id": str(tenant.id), "plan": new_plan},
        )
        period_end_dt = datetime.fromtimestamp(period_end_ts, tz=timezone.utc)
        tenant.pending_plan = new_plan
        tenant.pending_plan_date = period_end_dt.isoformat()
        logger.info(
            "Subscription downgrade scheduled",
            extra={"tenant_id": str(tenant.id), "new_plan": new_plan, "at": period_end_dt.isoformat()},
        )


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

    event_type = event["type"]
    raw = event["data"]["object"]
    obj = raw.to_dict() if hasattr(raw, "to_dict") else dict(raw)

    if event_type == "checkout.session.completed":
        await _handle_checkout_completed(obj, db)
    elif event_type == "invoice.paid":
        await _handle_invoice_paid(obj, db)
    elif event_type == "customer.subscription.updated":
        await _handle_subscription_updated(obj, db)
    elif event_type == "customer.subscription.deleted":
        await _handle_subscription_deleted(obj, db)
    else:
        logger.debug("Stripe webhook ignored", extra={"event_type": event_type})


async def _handle_checkout_completed(obj: dict, db: AsyncSession) -> None:
    metadata = obj.get("metadata", {})
    tenant_id = metadata.get("tenant_id")
    plan = metadata.get("plan")
    customer_id = obj.get("customer")
    subscription_id = obj.get("subscription")

    if not tenant_id or not plan:
        logger.error("checkout.session.completed missing metadata", extra={"metadata": metadata})
        return

    tenant = await _get_tenant(tenant_id, db)
    if tenant is None:
        logger.error("checkout.session.completed tenant not found", extra={"tenant_id": tenant_id})
        return

    duration = PLAN_DURATION_DAYS.get(plan, 30)
    expires_at = datetime.now(timezone.utc) + timedelta(days=duration)
    tenant.plan = plan
    tenant.plan_expires_at = expires_at.isoformat()
    if customer_id:
        tenant.stripe_customer_id = customer_id
    if subscription_id:
        tenant.stripe_subscription_id = subscription_id

    logger.info("Plan activated via checkout", extra={"tenant_id": tenant_id, "plan": plan})


async def _handle_invoice_paid(obj: dict, db: AsyncSession) -> None:
    customer_id = obj.get("customer")
    if not customer_id:
        return

    tenant = await _get_tenant_by_customer_id(customer_id, db)
    if tenant is None:
        logger.warning("invoice.paid tenant not found", extra={"customer_id": customer_id})
        return

    # Simpan subscription_id kalau belum ada
    lines = obj.get("lines", {}).get("data", [])
    if lines and not tenant.stripe_subscription_id:
        tenant.stripe_subscription_id = lines[0].get("subscription")

    # Kalau ada pending downgrade, ini adalah invoice renewal — terapkan sekarang
    if tenant.pending_plan:
        tenant.plan = tenant.pending_plan
        tenant.pending_plan = None
        tenant.pending_plan_date = None
        logger.info("Pending downgrade applied on renewal", extra={"tenant_id": str(tenant.id), "plan": tenant.plan})

    duration = PLAN_DURATION_DAYS.get(tenant.plan, 30)
    expires_at = datetime.now(timezone.utc) + timedelta(days=duration)
    tenant.plan_expires_at = expires_at.isoformat()

    logger.info("Plan renewed via invoice.paid", extra={"tenant_id": str(tenant.id), "plan": tenant.plan})


async def _handle_subscription_updated(obj: dict, db: AsyncSession) -> None:
    customer_id = obj.get("customer")
    subscription_id = obj.get("id")
    if not customer_id:
        return

    tenant = await _get_tenant_by_customer_id(customer_id, db)
    if tenant is None:
        logger.warning("subscription.updated tenant not found", extra={"customer_id": customer_id})
        return

    if subscription_id:
        tenant.stripe_subscription_id = subscription_id

    items = obj.get("items", {}).get("data", [])
    if not items:
        return

    price_id = items[0].get("price", {}).get("id")
    price_to_plan = {v: k for k, v in PLAN_PRICES.items()}
    new_plan = price_to_plan.get(price_id)
    if not new_plan:
        logger.warning("subscription.updated unknown price", extra={"price_id": price_id})
        return

    # Upgrade langsung aktif (bukan downgrade scheduled)
    if new_plan != tenant.plan and new_plan != tenant.pending_plan:
        duration = PLAN_DURATION_DAYS.get(new_plan, 30)
        expires_at = datetime.now(timezone.utc) + timedelta(days=duration)
        tenant.plan = new_plan
        tenant.plan_expires_at = expires_at.isoformat()
        tenant.pending_plan = None
        tenant.pending_plan_date = None
        logger.info("Plan updated via subscription.updated", extra={"tenant_id": str(tenant.id), "plan": new_plan})


async def _handle_subscription_deleted(obj: dict, db: AsyncSession) -> None:
    customer_id = obj.get("customer")
    if not customer_id:
        return

    tenant = await _get_tenant_by_customer_id(customer_id, db)
    if tenant is None:
        logger.warning("subscription.deleted tenant not found", extra={"customer_id": customer_id})
        return

    tenant.plan = "free"
    tenant.plan_expires_at = None
    tenant.stripe_subscription_id = None
    tenant.pending_plan = None
    tenant.pending_plan_date = None

    logger.info("Plan downgraded to free via subscription.deleted", extra={"tenant_id": str(tenant.id)})
