import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.billing_service import create_checkout_session, handle_stripe_webhook


def _mock_db():
    db = MagicMock()
    db.execute = AsyncMock()
    db.flush = AsyncMock()
    db.add = MagicMock()
    return db


def _make_tenant(tenant_id: uuid.UUID, plan: str = "free"):
    from app.models.tenant import Tenant
    t = Tenant(
        id=tenant_id,
        name="Test Tenant",
        email="test@example.com",
        plan=plan,
        ai_config={},
    )
    return t


@pytest.mark.asyncio
async def test_create_checkout_session_returns_url():
    tenant_id = str(uuid.uuid4())
    db = _mock_db()

    tenant = _make_tenant(uuid.UUID(tenant_id))
    execute_result = MagicMock()
    execute_result.scalar_one_or_none.return_value = tenant
    db.execute.return_value = execute_result

    mock_session = MagicMock()
    mock_session.url = "https://checkout.stripe.com/pay/cs_test_abc"
    mock_session.id = "cs_test_abc"

    with patch("stripe.checkout.Session.create", return_value=mock_session):
        with patch("stripe.Customer.create", return_value=MagicMock(id="cus_test123")):
            url = await create_checkout_session(
                tenant_id=tenant_id,
                plan="starter",
                success_url="https://app.test/billing?success=1",
                cancel_url="https://app.test/billing?cancel=1",
                db=db,
            )

    assert url == "https://checkout.stripe.com/pay/cs_test_abc"


@pytest.mark.asyncio
async def test_create_checkout_session_raises_if_tenant_not_found():
    tenant_id = str(uuid.uuid4())
    db = _mock_db()
    execute_result = MagicMock()
    execute_result.scalar_one_or_none.return_value = None
    db.execute.return_value = execute_result

    with pytest.raises(ValueError, match="Tenant tidak ditemukan"):
        await create_checkout_session(
            tenant_id=tenant_id,
            plan="starter",
            success_url="https://app.test/billing?success=1",
            cancel_url="https://app.test/billing?cancel=1",
            db=db,
        )


@pytest.mark.asyncio
async def test_handle_webhook_upgrades_plan():
    db = _mock_db()
    tenant_id = str(uuid.uuid4())
    tenant = _make_tenant(uuid.UUID(tenant_id))

    execute_result = MagicMock()
    execute_result.scalar_one_or_none.return_value = tenant
    db.execute.return_value = execute_result

    mock_event = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "metadata": {"tenant_id": tenant_id, "plan": "pro"},
                "customer": "cus_test123",
            }
        },
    }

    with patch("stripe.Webhook.construct_event", return_value=mock_event):
        await handle_stripe_webhook(b"payload", "sig_header", db)

    assert tenant.plan == "pro"
    assert tenant.stripe_customer_id == "cus_test123"
    assert tenant.plan_expires_at is not None


@pytest.mark.asyncio
async def test_handle_webhook_ignores_unknown_event():
    db = _mock_db()
    mock_event = {"type": "payment_intent.created", "data": {"object": {}}}

    with patch("stripe.Webhook.construct_event", return_value=mock_event):
        await handle_stripe_webhook(b"payload", "sig_header", db)

    db.execute.assert_not_called()
