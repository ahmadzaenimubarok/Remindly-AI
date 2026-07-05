from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


def test_billing_status_requires_auth(client):
    res = client.get("/api/v1/billing/status")
    assert res.status_code == 401


def test_billing_status_returns_plan():
    # Gunakan satu session agar cookie login tersimpan
    with TestClient(app, raise_server_exceptions=False) as c:
        c.post("/api/v1/auth/register", json={
            "name": "Billing Test",
            "email": "billingxtest2@test.com",
            "password": "Test1234!",
        })
        c.post("/api/v1/auth/login", json={
            "email": "billingxtest2@test.com",
            "password": "Test1234!",
        })
        res = c.get("/api/v1/billing/status")
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["data"]["plan"] == "free"
    assert "pending_plan" in data["data"]


def test_stripe_webhook_returns_200_on_valid_payload(client):
    with patch("app.routers.billing.handle_stripe_webhook", new_callable=AsyncMock) as mock_handler:
        mock_handler.return_value = None
        res = client.post(
            "/webhooks/stripe",
            content=b'{"type":"checkout.session.completed"}',
            headers={"stripe-signature": "t=1,v1=test"},
        )
    assert res.status_code == 200
    assert res.json() == {"received": True}


def test_stripe_webhook_returns_400_on_invalid_signature(client):
    with patch("app.routers.billing.handle_stripe_webhook", new_callable=AsyncMock) as mock_handler:
        mock_handler.side_effect = ValueError("Signature tidak valid")
        res = client.post(
            "/webhooks/stripe",
            content=b'{"type":"checkout.session.completed"}',
            headers={"stripe-signature": "bad-sig"},
        )
    assert res.status_code == 400
