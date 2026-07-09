import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.facebook_oauth_service import (
    exchange_code_for_token,
    exchange_to_long_lived_token,
    get_user_pages,
    subscribe_page_to_webhook,
    get_facebook_user_id,
    save_facebook_connection,
)


@pytest.mark.asyncio
async def test_exchange_code_for_token_success():
    mock_response = MagicMock()
    mock_response.is_success = True
    mock_response.json.return_value = {
        "access_token": "short-lived-token",
        "token_type": "bearer",
        "expires_in": 3600,
    }

    with patch("app.services.facebook_oauth_service.httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get = MagicMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client

        result = await exchange_code_for_token("auth-code-123")

    assert result is not None
    assert result["access_token"] == "short-lived-token"


@pytest.mark.asyncio
async def test_exchange_code_for_token_returns_none_on_error():
    with patch("app.services.facebook_oauth_service.httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get = MagicMock(side_effect=Exception("timeout"))
        mock_client_cls.return_value = mock_client

        result = await exchange_code_for_token("bad-code")

    assert result is None


@pytest.mark.asyncio
async def test_exchange_to_long_lived_token_success():
    mock_response = MagicMock()
    mock_response.is_success = True
    mock_response.json.return_value = {
        "access_token": "long-lived-token",
        "token_type": "bearer",
        "expires_in": 5184000,
    }

    with patch("app.services.facebook_oauth_service.httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get = MagicMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client

        result = await exchange_to_long_lived_token("short-lived-token")

    assert result is not None
    assert result["access_token"] == "long-lived-token"


@pytest.mark.asyncio
async def test_exchange_to_long_lived_token_returns_none_on_error():
    with patch("app.services.facebook_oauth_service.httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get = MagicMock(side_effect=Exception("connection refused"))
        mock_client_cls.return_value = mock_client

        result = await exchange_to_long_lived_token("bad-token")

    assert result is None


@pytest.mark.asyncio
async def test_get_user_pages_success():
    mock_response = MagicMock()
    mock_response.is_success = True
    mock_response.json.return_value = {
        "data": [
            {"id": "page-123", "name": "Toko Budi", "access_token": "page-token-1"},
            {"id": "page-456", "name": "Toko Ani", "access_token": "page-token-2"},
        ]
    }

    with patch("app.services.facebook_oauth_service.httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get = MagicMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client

        result = await get_user_pages("long-lived-token")

    assert len(result) == 2
    assert result[0]["id"] == "page-123"


@pytest.mark.asyncio
async def test_get_user_pages_returns_empty_on_error():
    with patch("app.services.facebook_oauth_service.httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get = MagicMock(side_effect=Exception("timeout"))
        mock_client_cls.return_value = mock_client

        result = await get_user_pages("bad-token")

    assert result == []


@pytest.mark.asyncio
async def test_subscribe_page_to_webhook_success():
    mock_response = MagicMock()
    mock_response.is_success = True

    with patch("app.services.facebook_oauth_service.httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post = MagicMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client

        result = await subscribe_page_to_webhook("page-123", "page-token")

    assert result is True


@pytest.mark.asyncio
async def test_subscribe_page_to_webhook_returns_false_on_error():
    with patch("app.services.facebook_oauth_service.httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post = MagicMock(side_effect=Exception("error"))
        mock_client_cls.return_value = mock_client

        result = await subscribe_page_to_webhook("page-123", "bad-token")

    assert result is False


@pytest.mark.asyncio
async def test_get_facebook_user_id_success():
    mock_response = MagicMock()
    mock_response.is_success = True
    mock_response.json.return_value = {"id": "fb-user-123"}

    with patch("app.services.facebook_oauth_service.httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get = MagicMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client

        result = await get_facebook_user_id("long-lived-token")

    assert result == "fb-user-123"


@pytest.mark.asyncio
async def test_get_facebook_user_id_returns_none_on_error():
    with patch("app.services.facebook_oauth_service.httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get = MagicMock(side_effect=Exception("error"))
        mock_client_cls.return_value = mock_client

        result = await get_facebook_user_id("bad-token")

    assert result is None


@pytest.mark.asyncio
async def test_save_facebook_connection_creates_new():
    import uuid

    db = MagicMock()
    db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))
    db.flush = AsyncMock()

    tenant_id = str(uuid.uuid4())

    with patch("app.services.facebook_oauth_service.encrypt_credential", return_value="encrypted-token"):
        result = await save_facebook_connection(
            tenant_id, "fb-user-456", "page-789", "page-token-xyz", db
        )

    db.add.assert_called_once()
    db.flush.assert_called_once()
