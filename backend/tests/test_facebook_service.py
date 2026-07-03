import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.facebook_service import send_comment_reply, send_messenger_reply


@pytest.mark.asyncio
async def test_send_comment_reply_success():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"id": "comment-123"}
    mock_response.raise_for_status = MagicMock()

    with patch("app.services.facebook_service.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client

        result = await send_comment_reply(
            page_token="token123",
            comment_id="comment-abc",
            message="Halo kak! Ada yang bisa dibantu?",
        )

    assert result is True


@pytest.mark.asyncio
async def test_send_comment_reply_returns_false_on_error():
    with patch("app.services.facebook_service.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(side_effect=httpx.HTTPError("connection failed"))
        mock_client_cls.return_value = mock_client

        result = await send_comment_reply("token", "comment-id", "pesan")

    assert result is False


@pytest.mark.asyncio
async def test_send_messenger_reply_success():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"recipient_id": "user-123", "message_id": "mid.123"}
    mock_response.raise_for_status = MagicMock()

    with patch("app.services.facebook_service.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client

        result = await send_messenger_reply(
            page_token="token123",
            recipient_id="user-abc",
            message="Halo! Terima kasih sudah DM kami.",
        )

    assert result is True


@pytest.mark.asyncio
async def test_send_messenger_reply_returns_false_on_error():
    with patch("app.services.facebook_service.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(side_effect=Exception("timeout"))
        mock_client_cls.return_value = mock_client

        result = await send_messenger_reply("token", "user-id", "pesan")

    assert result is False
