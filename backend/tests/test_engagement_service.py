import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.engagement_service import (
    process_facebook_comment,
    process_messenger_message,
    process_instagram_dm,
)


def _mock_db():
    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    return db


def _mock_tenant(tone: str = "casual", escalation_topics: list | None = None) -> MagicMock:
    t = MagicMock()
    t.id = uuid.uuid4()
    t.plan = "pro"
    t.name = "Toko Test"
    t.ai_config = {
        "tone": tone,
        "escalation_topics": escalation_topics or ["penipuan", "refund"],
    }
    return t


def _mock_credential() -> MagicMock:
    c = MagicMock()
    c.access_token_encrypted = "encrypted-token"
    c.is_expired.return_value = False
    return c


@pytest.mark.asyncio
async def test_process_facebook_comment_sends_reply():
    db = _mock_db()
    tenant_id = str(uuid.uuid4())
    tenant = _mock_tenant()
    credential = _mock_credential()

    event = {
        "comment_id": "cmnt-123",
        "message": "Kak harga berapa?",
        "from_id": "user-456",
        "from_name": "Budi",
        "post_id": "post-789",
    }

    with patch("app.services.engagement_service.check_feature_status") as mock_flag, \
         patch("app.services.engagement_service._get_tenant", return_value=tenant), \
         patch("app.services.engagement_service._get_facebook_credential", return_value=credential), \
         patch("app.services.engagement_service._get_or_create_customer") as mock_customer, \
         patch("app.services.engagement_service._get_conversation_by_platform_id", return_value=None), \
         patch("app.services.engagement_service.get_product_context", return_value="Produk: Tas Rajut | Harga: Rp 150.000"), \
         patch("app.services.engagement_service.classify_intent") as mock_intent, \
         patch("app.services.engagement_service.generate_reply", return_value="Harga Rp 150.000 kak!"), \
         patch("app.services.engagement_service.send_comment_reply", return_value=True), \
         patch("app.services.engagement_service.decrypt_credential", return_value="real-token"):

        from app.core.feature_flags import FeatureStatus
        mock_flag.return_value = FeatureStatus.ACTIVE

        mock_customer.return_value = MagicMock(id=uuid.uuid4())

        from app.services.openai_service import IntentResult
        mock_intent.return_value = IntentResult(
            intent="tanya_info", sentiment="neutral", confidence=0.9
        )

        await process_facebook_comment(tenant_id, event, db)

    db.add.assert_called()


@pytest.mark.asyncio
async def test_process_facebook_comment_skips_when_feature_not_active():
    db = _mock_db()
    tenant_id = str(uuid.uuid4())
    event = {"comment_id": "c1", "message": "test", "from_id": "u1", "from_name": "User", "post_id": "p1"}

    with patch("app.services.engagement_service.check_feature_status") as mock_flag, \
         patch("app.services.engagement_service.send_comment_reply") as mock_send:

        from app.core.feature_flags import FeatureStatus
        mock_flag.return_value = FeatureStatus.NOT_CONFIGURED

        await process_facebook_comment(tenant_id, event, db)

    mock_send.assert_not_called()


@pytest.mark.asyncio
async def test_process_facebook_comment_escalates_on_blacklist_topic():
    db = _mock_db()
    tenant_id = str(uuid.uuid4())
    tenant = _mock_tenant(escalation_topics=["refund", "penipuan"])
    credential = _mock_credential()

    event = {
        "comment_id": "cmnt-esc",
        "message": "Ini penipuan! Saya mau refund!",
        "from_id": "user-789",
        "from_name": "Andi",
        "post_id": "post-111",
    }

    saved_conversations = []

    def capture_add(obj):
        saved_conversations.append(obj)

    db.add = MagicMock(side_effect=capture_add)

    with patch("app.services.engagement_service.check_feature_status") as mock_flag, \
         patch("app.services.engagement_service._get_tenant", return_value=tenant), \
         patch("app.services.engagement_service._get_facebook_credential", return_value=credential), \
         patch("app.services.engagement_service._get_or_create_customer") as mock_customer, \
         patch("app.services.engagement_service._get_conversation_by_platform_id", return_value=None), \
         patch("app.services.engagement_service.get_product_context", return_value=""), \
         patch("app.services.engagement_service.classify_intent") as mock_intent, \
         patch("app.services.engagement_service.send_comment_reply") as mock_send, \
         patch("app.services.engagement_service.decrypt_credential", return_value="real-token"):

        from app.core.feature_flags import FeatureStatus
        mock_flag.return_value = FeatureStatus.ACTIVE
        mock_customer.return_value = MagicMock(id=uuid.uuid4())

        from app.services.openai_service import IntentResult
        mock_intent.return_value = IntentResult(
            intent="komplain", sentiment="negative", confidence=0.95
        )

        await process_facebook_comment(tenant_id, event, db)

    # Auto-reply tidak dikirim — eskalasi ke human
    mock_send.assert_not_called()

    # Conversation disimpan dengan is_human_takeover=True
    conv_objects = [o for o in saved_conversations if hasattr(o, "is_human_takeover")]
    assert any(o.is_human_takeover is True for o in conv_objects)


@pytest.mark.asyncio
async def test_process_facebook_comment_skips_if_already_human_takeover():
    db = _mock_db()
    tenant_id = str(uuid.uuid4())
    tenant = _mock_tenant()
    credential = _mock_credential()

    event = {
        "comment_id": "cmnt-ht",
        "message": "Halo lagi kak",
        "from_id": "user-ht",
        "from_name": "Cici",
        "post_id": "post-ht",
    }

    existing_conv = MagicMock()
    existing_conv.is_human_takeover = True

    with patch("app.services.engagement_service.check_feature_status") as mock_flag, \
         patch("app.services.engagement_service._get_tenant", return_value=tenant), \
         patch("app.services.engagement_service._get_facebook_credential", return_value=credential), \
         patch("app.services.engagement_service._get_or_create_customer") as mock_customer, \
         patch("app.services.engagement_service._get_conversation_by_platform_id", return_value=existing_conv), \
         patch("app.services.engagement_service.send_comment_reply") as mock_send, \
         patch("app.services.engagement_service.decrypt_credential", return_value="real-token"):

        from app.core.feature_flags import FeatureStatus
        mock_flag.return_value = FeatureStatus.ACTIVE
        mock_customer.return_value = MagicMock(id=uuid.uuid4())

        await process_facebook_comment(tenant_id, event, db)

    mock_send.assert_not_called()


# --- Instagram DM tests ---


@pytest.mark.asyncio
async def test_process_instagram_dm_sends_reply():
    db = _mock_db()
    tenant_id = str(uuid.uuid4())
    tenant = _mock_tenant()
    credential = _mock_credential()

    event = {
        "channel_type": "dm",
        "message_id": "ig-mid-123",
        "message": "Kak stok ada?",
        "sender_id": "igsid-456",
    }

    with patch("app.services.engagement_service.check_feature_status") as mock_flag, \
         patch("app.services.engagement_service._get_tenant", return_value=tenant), \
         patch("app.services.engagement_service._get_instagram_credential", return_value=credential), \
         patch("app.services.engagement_service._get_conversation_by_platform_id", return_value=None), \
         patch("app.services.engagement_service.get_instagram_user_name", return_value="Ani"), \
         patch("app.services.engagement_service._get_or_create_customer") as mock_customer, \
         patch("app.services.engagement_service._get_or_create_session") as mock_session, \
         patch("app.services.engagement_service.get_product_context", return_value="Produk: Tas | Harga: 100k"), \
         patch("app.services.engagement_service.classify_intent") as mock_intent, \
         patch("app.services.engagement_service.generate_reply", return_value="Stok masih ada kak!"), \
         patch("app.services.engagement_service.send_instagram_dm", return_value=True), \
         patch("app.services.engagement_service.decrypt_credential", return_value="real-token"):

        from app.core.feature_flags import FeatureStatus
        mock_flag.return_value = FeatureStatus.ACTIVE

        mock_customer.return_value = MagicMock(id=uuid.uuid4())
        mock_session_obj = MagicMock()
        mock_session_obj.id = uuid.uuid4()
        mock_session_obj.status = "open"
        mock_session.return_value = (mock_session_obj, [])

        from app.services.openai_service import IntentResult
        mock_intent.return_value = IntentResult(
            intent="tanya_info", sentiment="neutral", confidence=0.9
        )

        result = await process_instagram_dm(tenant_id, event, db)

    assert result is not None
    db.add.assert_called()


@pytest.mark.asyncio
async def test_process_instagram_dm_skips_when_feature_not_active():
    db = _mock_db()
    tenant_id = str(uuid.uuid4())
    event = {
        "channel_type": "dm",
        "message_id": "ig-mid-skip",
        "message": "test",
        "sender_id": "igsid-skip",
    }

    with patch("app.services.engagement_service.check_feature_status") as mock_flag, \
         patch("app.services.engagement_service.send_instagram_dm") as mock_send:

        from app.core.feature_flags import FeatureStatus
        mock_flag.return_value = FeatureStatus.NOT_CONFIGURED

        result = await process_instagram_dm(tenant_id, event, db)

    assert result is None
    mock_send.assert_not_called()


@pytest.mark.asyncio
async def test_process_instagram_dm_skips_no_credential():
    db = _mock_db()
    tenant_id = str(uuid.uuid4())
    tenant = _mock_tenant()
    event = {
        "channel_type": "dm",
        "message_id": "ig-mid-nocred",
        "message": "test",
        "sender_id": "igsid-nocred",
    }

    with patch("app.services.engagement_service.check_feature_status") as mock_flag, \
         patch("app.services.engagement_service._get_tenant", return_value=tenant), \
         patch("app.services.engagement_service._get_instagram_credential", return_value=None), \
         patch("app.services.engagement_service.send_instagram_dm") as mock_send:

        from app.core.feature_flags import FeatureStatus
        mock_flag.return_value = FeatureStatus.ACTIVE

        result = await process_instagram_dm(tenant_id, event, db)

    assert result is None
    mock_send.assert_not_called()


@pytest.mark.asyncio
async def test_process_instagram_dm_escalates_on_blacklist_topic():
    db = _mock_db()
    tenant_id = str(uuid.uuid4())
    tenant = _mock_tenant(escalation_topics=["refund"])
    credential = _mock_credential()

    event = {
        "channel_type": "dm",
        "message_id": "ig-mid-esc",
        "message": "Saya mau refund!",
        "sender_id": "igsid-esc",
    }

    saved_conversations = []

    def capture_add(obj):
        saved_conversations.append(obj)

    db.add = MagicMock(side_effect=capture_add)

    with patch("app.services.engagement_service.check_feature_status") as mock_flag, \
         patch("app.services.engagement_service._get_tenant", return_value=tenant), \
         patch("app.services.engagement_service._get_instagram_credential", return_value=credential), \
         patch("app.services.engagement_service._get_conversation_by_platform_id", return_value=None), \
         patch("app.services.engagement_service.get_instagram_user_name", return_value="User"), \
         patch("app.services.engagement_service._get_or_create_customer") as mock_customer, \
         patch("app.services.engagement_service._get_or_create_session") as mock_session, \
         patch("app.services.engagement_service.get_product_context", return_value=""), \
         patch("app.services.engagement_service.classify_intent") as mock_intent, \
         patch("app.services.engagement_service.send_instagram_dm") as mock_send, \
         patch("app.services.engagement_service.decrypt_credential", return_value="real-token"):

        from app.core.feature_flags import FeatureStatus
        mock_flag.return_value = FeatureStatus.ACTIVE

        mock_customer.return_value = MagicMock(id=uuid.uuid4())
        mock_session_obj = MagicMock()
        mock_session_obj.id = uuid.uuid4()
        mock_session.return_value = (mock_session_obj, [])

        from app.services.openai_service import IntentResult
        mock_intent.return_value = IntentResult(
            intent="komplain", sentiment="negative", confidence=0.95
        )

        await process_instagram_dm(tenant_id, event, db)

    mock_send.assert_not_called()
    conv_objects = [o for o in saved_conversations if hasattr(o, "is_human_takeover")]
    assert any(o.is_human_takeover is True for o in conv_objects)


@pytest.mark.asyncio
async def test_process_instagram_dm_skips_duplicate():
    db = _mock_db()
    tenant_id = str(uuid.uuid4())
    tenant = _mock_tenant()
    credential = _mock_credential()

    event = {
        "channel_type": "dm",
        "message_id": "ig-mid-dup",
        "message": "Halo lagi",
        "sender_id": "igsid-dup",
    }

    existing_conv = MagicMock()
    existing_conv.is_human_takeover = False

    with patch("app.services.engagement_service.check_feature_status") as mock_flag, \
         patch("app.services.engagement_service._get_tenant", return_value=tenant), \
         patch("app.services.engagement_service._get_instagram_credential", return_value=credential), \
         patch("app.services.engagement_service._get_conversation_by_platform_id", return_value=existing_conv), \
         patch("app.services.engagement_service.send_instagram_dm") as mock_send, \
         patch("app.services.engagement_service.decrypt_credential", return_value="real-token"):

        from app.core.feature_flags import FeatureStatus
        mock_flag.return_value = FeatureStatus.ACTIVE

        result = await process_instagram_dm(tenant_id, event, db)

    assert result is None
    mock_send.assert_not_called()
