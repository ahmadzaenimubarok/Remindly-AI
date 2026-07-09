from unittest.mock import AsyncMock, patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def auth_client():
    with TestClient(app, raise_server_exceptions=False) as c:
        c.post(
            "/api/v1/auth/register",
            json={
                "name": "FB OAuth Test",
                "email": "fboauth@test.com",
                "password": "Test1234!",
            },
        )
        c.post(
            "/api/v1/auth/login",
            json={
                "email": "fboauth@test.com",
                "password": "Test1234!",
            },
        )
        yield c


def test_facebook_login_redirects_to_facebook(auth_client):
    with patch("app.routers.facebook_oauth.get_settings") as mock_settings:
        mock_settings.return_value = MagicMock(
            META_APP_ID="123456",
            META_REDIRECT_URI="http://localhost:8000/api/v1/auth/facebook/callback",
        )
        res = auth_client.get("/api/v1/auth/facebook/login")

    assert res.status_code == 200
    assert "facebook.com" in res.json()["url"]
    assert "client_id=123456" in res.json()["url"]


def test_facebook_login_requires_auth():
    with TestClient(app, raise_server_exceptions=False) as c:
        res = c.get("/api/v1/auth/facebook/login")
    assert res.status_code == 401


def test_facebook_callback_redirects_to_frontend_on_success(auth_client):
    mock_token_response = {
        "access_token": "short-lived-token",
        "expires_in": 3600,
    }
    mock_long_token_response = {
        "access_token": "long-lived-token",
        "expires_in": 5184000,
    }
    mock_user_id = "fb-user-123"
    mock_pages = [
        {"id": "page-1", "name": "Toko Budi", "access_token": "page-token-1"},
    ]

    with patch(
        "app.routers.facebook_oauth.exchange_code_for_token",
        new_callable=AsyncMock,
    ) as mock_exchange, patch(
        "app.routers.facebook_oauth.exchange_to_long_lived_token",
        new_callable=AsyncMock,
    ) as mock_long, patch(
        "app.routers.facebook_oauth.get_facebook_user_id",
        new_callable=AsyncMock,
    ) as mock_uid, patch(
        "app.routers.facebook_oauth.get_user_pages",
        new_callable=AsyncMock,
    ) as mock_pages_fn, patch(
        "app.routers.facebook_oauth.get_settings",
    ) as mock_settings:
        mock_exchange.return_value = mock_token_response
        mock_long.return_value = mock_long_token_response
        mock_uid.return_value = mock_user_id
        mock_pages_fn.return_value = mock_pages
        mock_settings.return_value = MagicMock(
            FRONTEND_URL="http://localhost:3000",
        )

        res = auth_client.get(
            "/api/v1/auth/facebook/callback",
            params={"code": "auth-code-123", "state": "tenant-123"},
            follow_redirects=False,
        )

    assert res.status_code == 307
    assert "localhost:3000/auth/facebook/callback" in res.headers["location"]
    assert "data=" in res.headers["location"]


def test_facebook_callback_redirects_on_exchange_failure(auth_client):
    with patch(
        "app.routers.facebook_oauth.exchange_code_for_token",
        new_callable=AsyncMock,
    ) as mock_exchange, patch(
        "app.routers.facebook_oauth.get_settings",
    ) as mock_settings:
        mock_exchange.return_value = None
        mock_settings.return_value = MagicMock(
            FRONTEND_URL="http://localhost:3000",
        )

        res = auth_client.get(
            "/api/v1/auth/facebook/callback",
            params={"code": "bad-code", "state": "tenant-123"},
            follow_redirects=False,
        )

    assert res.status_code == 307
    assert "error=exchange_failed" in res.headers["location"]


def test_facebook_callback_redirects_on_facebook_error(auth_client):
    with patch("app.routers.facebook_oauth.get_settings") as mock_settings:
        mock_settings.return_value = MagicMock(
            FRONTEND_URL="http://localhost:3000",
        )

        res = auth_client.get(
            "/api/v1/auth/facebook/callback",
            params={"error": "access_denied", "state": "tenant-123"},
            follow_redirects=False,
        )

    assert res.status_code == 307
    assert "error=access_denied" in res.headers["location"]


def test_facebook_connect_saves_connection(auth_client):
    with patch(
        "app.routers.facebook_oauth.save_facebook_connection",
        new_callable=AsyncMock,
    ) as mock_save, patch(
        "app.routers.facebook_oauth.subscribe_page_to_webhook",
        new_callable=AsyncMock,
    ) as mock_subscribe:
        mock_save.return_value = MagicMock()
        mock_subscribe.return_value = True

        res = auth_client.post(
            "/api/v1/auth/facebook/connect",
            json={
                "page_id": "page-123",
                "page_name": "Toko Budi",
                "access_token": "page-token-xyz",
            },
        )

    assert res.status_code == 200
    mock_save.assert_called_once()
    mock_subscribe.assert_called_once()


def test_facebook_disconnect_removes_connection(auth_client):
    with patch(
        "app.routers.facebook_oauth.disconnect_facebook_connection",
        new_callable=AsyncMock,
    ) as mock_disconnect:
        mock_disconnect.return_value = None
        res = auth_client.delete("/api/v1/auth/facebook/disconnect")

    assert res.status_code == 200
    assert "berhasil dihapus" in res.json()["message"]
    mock_disconnect.assert_called_once()
