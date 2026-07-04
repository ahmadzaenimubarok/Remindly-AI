import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.schemas.auth import LoginRequest, RegisterRequest
from app.services.auth_service import login_user, refresh_access_token, register_user


def _mock_db():
    db = AsyncMock()
    db.flush = AsyncMock()
    db.add = MagicMock()
    return db


@pytest.mark.asyncio
async def test_register_user_success():
    db = _mock_db()
    body = RegisterRequest(name="Toko Kece", email="toko@test.com", password="secret123")

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=mock_result)

    with patch("app.services.auth_service.provision_tenant") as mock_provision:
        mock_tenant = MagicMock()
        mock_tenant.id = uuid.uuid4()
        mock_provision.return_value = mock_tenant

        user, tenant = await register_user(body, db)

    assert user.email == "toko@test.com"
    assert user.role == "tenant_user"
    assert tenant is mock_tenant


@pytest.mark.asyncio
async def test_register_duplicate_email_raises_409():
    db = _mock_db()
    body = RegisterRequest(name="Toko", email="exists@test.com", password="secret123")

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = MagicMock()
    db.execute = AsyncMock(return_value=mock_result)

    with pytest.raises(HTTPException) as exc:
        await register_user(body, db)

    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_login_invalid_password_raises_401():
    db = _mock_db()
    body = LoginRequest(email="user@test.com", password="wrongpass")

    mock_user = MagicMock()
    mock_user.password_hash = "hashed"
    mock_user.is_active = True

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_user
    db.execute = AsyncMock(return_value=mock_result)

    with patch("app.services.auth_service.verify_password", return_value=False):
        with pytest.raises(HTTPException) as exc:
            await login_user(body, db)

    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_login_success_returns_tokens():
    db = _mock_db()
    body = LoginRequest(email="user@test.com", password="correctpass")

    mock_user = MagicMock()
    mock_user.id = uuid.uuid4()
    mock_user.tenant_id = uuid.uuid4()
    mock_user.role = "tenant_user"
    mock_user.is_active = True
    mock_user.password_hash = "hashed"

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_user
    db.execute = AsyncMock(return_value=mock_result)

    with patch("app.services.auth_service.verify_password", return_value=True):
        response = await login_user(body, db)

    assert response.access_token
    assert response.refresh_token


@pytest.mark.asyncio
async def test_refresh_with_invalid_token_raises_401():
    db = _mock_db()

    with pytest.raises(HTTPException) as exc:
        await refresh_access_token("invalid.token", db)

    assert exc.value.status_code == 401
