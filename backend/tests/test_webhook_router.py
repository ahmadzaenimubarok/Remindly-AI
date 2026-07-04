from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import get_settings


@pytest.fixture
def client():
    # Disable signature validation di test — META_APP_SECRET tidak diset di test env
    with patch("app.routers.webhooks.get_settings") as mock_settings:
        s = get_settings()
        s.META_APP_SECRET = None
        mock_settings.return_value = s
        with TestClient(app, raise_server_exceptions=False) as c:
            yield c


def test_facebook_verify_success(client):
    settings = get_settings()
    res = client.get("/webhooks/facebook", params={
        "hub.mode": "subscribe",
        "hub.verify_token": settings.META_VERIFY_TOKEN,
        "hub.challenge": "challenge-abc123",
    })
    assert res.status_code == 200
    assert res.text == "challenge-abc123"


def test_facebook_verify_wrong_token_returns_403(client):
    res = client.get("/webhooks/facebook", params={
        "hub.mode": "subscribe",
        "hub.verify_token": "wrong-token",
        "hub.challenge": "challenge-xyz",
    })
    assert res.status_code == 403


def test_facebook_receive_comment_event(client):
    payload = {
        "object": "page",
        "entry": [{
            "id": "page-123",
            "changes": [{
                "field": "feed",
                "value": {
                    "item": "comment",
                    "comment_id": "cmnt-abc",
                    "message": "Harga berapa?",
                    "from": {"id": "user-1", "name": "Budi"},
                    "post_id": "post-1",
                }
            }]
        }]
    }

    with patch("app.routers.webhooks.process_facebook_event") as mock_task:
        mock_task.delay = MagicMock()
        res = client.post(
            "/webhooks/facebook",
            params={"tenant_id": "00000000-0000-0000-0000-000000000001"},
            json=payload,
        )

    assert res.status_code == 200
    assert res.json()["queued"] == 1


def test_facebook_receive_messenger_event(client):
    payload = {
        "object": "page",
        "entry": [{
            "id": "page-123",
            "messaging": [{
                "sender": {"id": "user-2"},
                "recipient": {"id": "page-123"},
                "message": {"mid": "m123", "text": "Halo kak!"},
            }]
        }]
    }

    with patch("app.routers.webhooks.process_facebook_event") as mock_task:
        mock_task.delay = MagicMock()
        res = client.post(
            "/webhooks/facebook",
            params={"tenant_id": "00000000-0000-0000-0000-000000000001"},
            json=payload,
        )

    assert res.status_code == 200
    assert res.json()["queued"] == 1


def test_facebook_receive_ignores_non_page_object(client):
    payload = {"object": "user", "entry": []}

    with patch("app.routers.webhooks.process_facebook_event") as mock_task:
        mock_task.delay = MagicMock()
        res = client.post(
            "/webhooks/facebook",
            params={"tenant_id": "00000000-0000-0000-0000-000000000001"},
            json=payload,
        )

    assert res.status_code == 200
    assert res.json()["status"] == "ignored"
    mock_task.delay.assert_not_called()


def test_facebook_receive_invalid_payload_returns_400(client):
    res = client.post(
        "/webhooks/facebook",
        params={"tenant_id": "00000000-0000-0000-0000-000000000001"},
        content=b"ini bukan json",
        headers={"Content-Type": "application/json"},
    )
    assert res.status_code == 400
