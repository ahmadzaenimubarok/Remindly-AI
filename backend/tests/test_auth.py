import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def test_health(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_register_success(client):
    mock_tenant = MagicMock()
    mock_tenant.id = uuid.uuid4()
    mock_tenant.name = "Toko Kece"
    mock_tenant.email = "toko@test.com"
    mock_tenant.plan = "free"
    mock_user = MagicMock()

    with patch("app.routers.auth.register_user", new_callable=AsyncMock) as mock_reg:
        mock_reg.return_value = (mock_user, mock_tenant)
        res = client.post("/api/v1/auth/register", json={
            "name": "Toko Kece",
            "email": "toko@test.com",
            "password": "secret123",
        })

    assert res.status_code == 201
    assert res.json()["success"] is True
    assert res.json()["data"]["email"] == "toko@test.com"


def test_register_invalid_email_returns_422(client):
    res = client.post("/api/v1/auth/register", json={
        "name": "Toko",
        "email": "bukan-email",
        "password": "secret123",
    })
    assert res.status_code == 422
    assert res.json()["success"] is False
    assert res.json()["code"] == "VALIDATION_ERROR"


def test_login_success_sets_cookies(client):
    from app.services.auth_service import TokenPair
    mock_tokens = TokenPair(
        access_token="access.token.here",
        refresh_token="refresh.token.here",
    )

    with patch("app.routers.auth.login_user", new_callable=AsyncMock) as mock_login:
        mock_login.return_value = mock_tokens
        res = client.post("/api/v1/auth/login", json={
            "email": "user@test.com",
            "password": "secret123",
        })

    assert res.status_code == 200
    assert res.json()["data"]["token_type"] == "bearer"
    # Token ada di cookie, bukan di body
    assert "access_token" not in res.json()["data"]
    assert "access_token" in res.cookies


def test_login_wrong_credentials_returns_401(client):
    from fastapi import HTTPException

    with patch("app.routers.auth.login_user", new_callable=AsyncMock) as mock_login:
        mock_login.side_effect = HTTPException(status_code=401, detail="Email atau password salah.")
        res = client.post("/api/v1/auth/login", json={
            "email": "user@test.com",
            "password": "wrongpass",
        })

    assert res.status_code == 401


def test_protected_endpoint_without_token_returns_401(client):
    res = client.get("/api/v1/some-protected-route")
    assert res.status_code == 401
    assert res.json()["code"] == "UNAUTHORIZED"


def test_logout_returns_success(client):
    res = client.post("/api/v1/auth/logout")
    assert res.status_code == 200
    assert res.json()["success"] is True


def test_me_without_token_returns_401(client):
    res = client.get("/api/v1/auth/me")
    assert res.status_code == 401


def test_me_with_valid_token_returns_user_info(client):
    from app.core.security import create_access_token
    token = create_access_token({
        "sub": str(uuid.uuid4()),
        "tenant_id": str(uuid.uuid4()),
        "role": "tenant_user",
    })
    client.cookies.set("access_token", token)
    res = client.get("/api/v1/auth/me")
    client.cookies.clear()
    assert res.status_code == 200
    data = res.json()["data"]
    assert "user_id" in data
    assert "tenant_id" in data
    assert data["role"] == "tenant_user"


def test_me_with_invalid_token_returns_401(client):
    client.cookies.set("access_token", "invalid.token.here")
    res = client.get("/api/v1/auth/me")
    client.cookies.clear()
    assert res.status_code == 401
