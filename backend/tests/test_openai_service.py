from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.openai_service import IntentResult, classify_intent, generate_reply


@pytest.mark.asyncio
async def test_classify_intent_returns_intent_result():
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = (
        '{"intent": "tanya_info", "sentiment": "neutral", "confidence": 0.92}'
    )

    with patch("app.services.openai_service.get_llm_client") as mock_client_fn:
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_client_fn.return_value = mock_client

        result = await classify_intent(
            message="Harga berapa kak?",
            tenant_context="Toko fashion wanita",
        )

    assert isinstance(result, IntentResult)
    assert result.intent == "tanya_info"
    assert result.sentiment == "neutral"
    assert result.confidence == 0.92


@pytest.mark.asyncio
async def test_classify_intent_fallback_on_invalid_json():
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "ini bukan json"

    with patch("app.services.openai_service.get_llm_client") as mock_client_fn:
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_client_fn.return_value = mock_client

        result = await classify_intent("pesan", "context")

    assert result.intent == "tanya_info"
    assert result.confidence == 0.0


@pytest.mark.asyncio
async def test_generate_reply_returns_string():
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Halo kak! Ada yang bisa dibantu? 😊"

    with patch("app.services.openai_service.get_llm_client") as mock_client_fn:
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_client_fn.return_value = mock_client

        reply = await generate_reply(
            message="Halo ada diskon ga?",
            context="Produk: Tas Rajut, harga Rp 150.000",
            tone="casual",
        )

    assert isinstance(reply, str)
    assert len(reply) > 0


@pytest.mark.asyncio
async def test_generate_reply_fallback_on_exception():
    with patch("app.services.openai_service.get_llm_client") as mock_client_fn:
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=Exception("API down")
        )
        mock_client_fn.return_value = mock_client

        reply = await generate_reply("pesan", "context", "casual")

    assert reply == "Halo! Terima kasih sudah menghubungi kami. Tim kami akan segera membalas pesanmu ya 🙏"
