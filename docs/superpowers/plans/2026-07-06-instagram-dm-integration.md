# Instagram DM Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tambah dukungan Instagram Direct Messages ke sistem engagement — webhook endpoint, service layer, dan Celery worker — tanpa mengubah kode Facebook yang sudah berjalan.

**Architecture:** Mirror pola Facebook/Messenger yang ada. Instagram pakai Meta Graph API yang sama, sehingga signature verification, payload schema, dan format API call hampir identik. Shared helpers di `engagement_service.py` (`_get_or_create_customer`, `_get_or_create_session`, `_should_escalate`, dll.) dipakai langsung tanpa modifikasi.

**Tech Stack:** FastAPI, SQLAlchemy async, Celery, httpx, pytest

## Global Constraints

- Python 3.12+
- Graph API base URL: `https://graph.facebook.com/v21.0` (sama dengan Facebook)
- Platform string DB: `"instagram"` (bukan `"ig"` atau `"Instagram"`)
- Channel type: `"dm"`
- Feature flag key: `"instagram_reply"` (sudah ada di `PLAN_FEATURES`)
- Celery queue: `"engagement"` (sama dengan Facebook worker)
- Tidak ada perubahan DB schema, `.env`, atau `config.py`
- Tidak ada perubahan pada fungsi Facebook yang sudah ada
- Ikuti pola test yang ada: `unittest.mock`, `pytest.mark.asyncio`, patch by dotted path

---

## File Map

| File | Action | Tanggung jawab |
|---|---|---|
| `backend/app/services/instagram_service.py` | **Create** | API call ke Meta Graph API untuk Instagram |
| `backend/app/services/engagement_service.py` | **Edit** | Tambah `_get_instagram_credential` + `process_instagram_dm` |
| `backend/workers/engagement_worker.py` | **Edit** | Tambah Celery task `process_instagram_event` |
| `backend/app/routers/webhooks.py` | **Edit** | Tambah GET + POST `/webhooks/instagram` |
| `backend/tests/test_instagram_service.py` | **Create** | Unit test untuk instagram_service |
| `backend/tests/test_engagement_service.py` | **Edit** | Tambah test untuk `process_instagram_dm` |
| `backend/tests/test_engagement_worker.py` | **Edit** | Tambah test untuk `process_instagram_event` |
| `backend/tests/test_webhook_router.py` | **Edit** | Tambah test untuk endpoint `/webhooks/instagram` |

---

## Task 1: Instagram Service — API calls ke Meta Graph API

**Files:**
- Create: `backend/app/services/instagram_service.py`
- Test: `backend/tests/test_instagram_service.py`

**Interfaces:**
- Produces:
  - `get_instagram_user_name(page_token: str, igsid: str) -> str | None`
  - `send_instagram_dm(page_token: str, recipient_igsid: str, message: str) -> bool`

- [ ] **Step 1: Tulis failing test untuk `get_instagram_user_name` — success case**

Buat file `backend/tests/test_instagram_service.py`:

```python
import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.instagram_service import get_instagram_user_name, send_instagram_dm


@pytest.mark.asyncio
async def test_get_instagram_user_name_returns_name():
    mock_response = MagicMock()
    mock_response.is_success = True
    mock_response.json.return_value = {"name": "Budi Santoso", "username": "budi.s"}

    with patch("app.services.instagram_service.httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get = MagicMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client

        result = await get_instagram_user_name("token123", "igsid-abc")

    assert result == "Budi Santoso"


@pytest.mark.asyncio
async def test_get_instagram_user_name_falls_back_to_username():
    mock_response = MagicMock()
    mock_response.is_success = True
    mock_response.json.return_value = {"username": "budi.s"}

    with patch("app.services.instagram_service.httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get = MagicMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client

        result = await get_instagram_user_name("token123", "igsid-abc")

    assert result == "budi.s"


@pytest.mark.asyncio
async def test_get_instagram_user_name_returns_none_on_error():
    with patch("app.services.instagram_service.httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get = MagicMock(side_effect=Exception("timeout"))
        mock_client_cls.return_value = mock_client

        result = await get_instagram_user_name("token", "igsid")

    assert result is None


@pytest.mark.asyncio
async def test_send_instagram_dm_success():
    mock_response = MagicMock()
    mock_response.is_success = True

    with patch("app.services.instagram_service.httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post = MagicMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client

        result = await send_instagram_dm("token123", "igsid-abc", "Halo kak!")

    assert result is True


@pytest.mark.asyncio
async def test_send_instagram_dm_returns_false_on_error():
    with patch("app.services.instagram_service.httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post = MagicMock(side_effect=Exception("connection refused"))
        mock_client_cls.return_value = mock_client

        result = await send_instagram_dm("token", "igsid", "pesan")

    assert result is False


@pytest.mark.asyncio
async def test_send_instagram_dm_returns_false_on_non_success_status():
    mock_response = MagicMock()
    mock_response.is_success = False
    mock_response.status_code = 400
    mock_response.text = "Bad Request"

    with patch("app.services.instagram_service.httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post = MagicMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client

        result = await send_instagram_dm("token", "igsid", "pesan")

    assert result is False
```

- [ ] **Step 2: Jalankan test — verifikasi FAIL**

```bash
cd backend && python -m pytest tests/test_instagram_service.py -v 2>&1 | head -30
```

Expected: `ImportError` atau `ModuleNotFoundError` karena file belum ada.

- [ ] **Step 3: Buat `instagram_service.py`**

Buat file `backend/app/services/instagram_service.py`:

```python
import logging

import httpx

logger = logging.getLogger(__name__)

GRAPH_API_BASE = "https://graph.facebook.com/v21.0"


async def get_instagram_user_name(page_token: str, igsid: str) -> str | None:
    """Fetch nama/username user Instagram via Graph API. Return None jika gagal."""
    url = f"{GRAPH_API_BASE}/{igsid}"
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(
                url,
                params={"access_token": page_token, "fields": "name,username"},
            )
            if response.is_success:
                data = response.json()
                return data.get("name") or data.get("username")
    except Exception:
        logger.warning("get_instagram_user_name failed", extra={"igsid": igsid})
    return None


async def send_instagram_dm(page_token: str, recipient_igsid: str, message: str) -> bool:
    """Kirim DM Instagram via Graph API. Kembalikan True jika berhasil."""
    url = f"{GRAPH_API_BASE}/me/messages"
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                url,
                params={"access_token": page_token},
                json={
                    "recipient": {"id": recipient_igsid},
                    "message": {"text": message},
                    "messaging_type": "RESPONSE",
                },
            )
            if not response.is_success:
                logger.error(
                    f"send_instagram_dm failed status={response.status_code} body={response.text!r}"
                )
                return False
            logger.info("Instagram DM sent", extra={"recipient_igsid": recipient_igsid})
            return True
    except Exception:
        logger.exception("send_instagram_dm failed", extra={"recipient_igsid": recipient_igsid})
        return False
```

- [ ] **Step 4: Jalankan test — verifikasi PASS**

```bash
cd backend && python -m pytest tests/test_instagram_service.py -v
```

Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
cd backend && git add app/services/instagram_service.py tests/test_instagram_service.py
git commit -m "feat: add instagram_service — get_instagram_user_name, send_instagram_dm"
```

---

## Task 2: Engagement Service — `_get_instagram_credential` + `process_instagram_dm`

**Files:**
- Modify: `backend/app/services/engagement_service.py`
- Test: `backend/tests/test_engagement_service.py`

**Interfaces:**
- Consumes:
  - `get_instagram_user_name(page_token: str, igsid: str) -> str | None` (Task 1)
  - `send_instagram_dm(page_token: str, recipient_igsid: str, message: str) -> bool` (Task 1)
  - Shared helpers sudah ada: `_get_tenant`, `_get_or_create_customer`, `_get_or_create_session`, `_get_conversation_by_platform_id`, `_should_escalate`, `_is_closing_signal`, `_save_system_log`, `check_feature_status`, `decrypt_credential`, `get_product_context`, `classify_intent`, `generate_reply`
- Produces:
  - `process_instagram_dm(tenant_id: str, event: dict, db: AsyncSession) -> str | None`
  - `_get_instagram_credential(tenant_id: str, db: AsyncSession) -> TenantCredential | None` (private)

- [ ] **Step 1: Tulis failing tests**

Tambahkan ke `backend/tests/test_engagement_service.py` (append setelah isi yang ada):

```python
# --- Instagram DM tests ---

from app.services.engagement_service import process_instagram_dm


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
```

- [ ] **Step 2: Jalankan test — verifikasi FAIL**

```bash
cd backend && python -m pytest tests/test_engagement_service.py::test_process_instagram_dm_sends_reply -v 2>&1 | tail -10
```

Expected: `ImportError: cannot import name 'process_instagram_dm'`

- [ ] **Step 3: Tambahkan `_get_instagram_credential` dan `process_instagram_dm` ke engagement_service.py**

Tambahkan import di bagian atas file, setelah baris import `facebook_service`:

```python
from app.services.instagram_service import get_instagram_user_name, send_instagram_dm
```

Tambahkan helper `_get_instagram_credential` setelah `_get_facebook_credential` (sekitar baris 47):

```python
async def _get_instagram_credential(
    tenant_id: str, db: AsyncSession
) -> TenantCredential | None:
    result = await db.execute(
        select(TenantCredential).where(
            TenantCredential.tenant_id == uuid.UUID(tenant_id),
            TenantCredential.platform == "instagram",
        )
    )
    return result.scalar_one_or_none()
```

Tambahkan fungsi `process_instagram_dm` di akhir file:

```python
async def process_instagram_dm(
    tenant_id: str, event: dict, db: AsyncSession
) -> str | None:
    """
    Proses event Instagram DM untuk satu tenant.
    event keys: message_id, message, sender_id
    """
    message_id: str = event["message_id"]
    message: str = event["message"]
    sender_id: str = event["sender_id"]

    status = await check_feature_status(tenant_id, "instagram_reply", db)
    if status != FeatureStatus.ACTIVE:
        await log_skip(tenant_id, "instagram_reply", status)
        return None

    tenant = await _get_tenant(tenant_id, db)
    if tenant is None:
        logger.error("Tenant not found", extra={"tenant_id": tenant_id})
        return None

    credential = await _get_instagram_credential(tenant_id, db)
    if credential is None or credential.is_expired():
        await _save_system_log(
            tenant_id, "instagram_dm_reply", "skipped",
            {"reason": "no_credential", "message_id": message_id}, db,
        )
        return None

    existing = await _get_conversation_by_platform_id(tenant_id, message_id, db)
    if existing is not None:
        return None

    page_token = decrypt_credential(credential.access_token_encrypted)
    sender_name = await get_instagram_user_name(page_token, sender_id)
    customer = await _get_or_create_customer(tenant_id, sender_id, "instagram", sender_name, db)

    session, prior_context_msgs = await _get_or_create_session(
        tenant_id, customer.id, "instagram", "dm", message, db
    )
    prior_context_str = "\n".join(prior_context_msgs) if prior_context_msgs else None

    product_context = await get_product_context(tenant_id, message, db)
    tenant_context = f"Nama toko: {tenant.name}\n{product_context}"

    intent_result = await classify_intent(message, tenant_context)

    escalation_topics: list[str] = tenant.ai_config.get("escalation_topics", [])
    should_escalate, escalation_reason = _should_escalate(message, intent_result, escalation_topics)

    if should_escalate:
        conv = Conversation(
            tenant_id=uuid.UUID(tenant_id),
            customer_id=customer.id,
            session_id=session.id,
            platform="instagram",
            channel_type="dm",
            platform_message_id=message_id,
            message_in=message,
            message_out=None,
            intent=intent_result.intent,
            sentiment=intent_result.sentiment,
            is_human_takeover=True,
            escalation_reason=escalation_reason,
        )
        db.add(conv)
        await _save_system_log(
            tenant_id, "instagram_dm_escalated", "success",
            {"message_id": message_id, "reason": escalation_reason}, db,
        )
        return str(customer.id)

    tone = tenant.ai_config.get("tone", "casual")
    reply = await generate_reply(message, product_context, tone, prior_context=prior_context_str)
    sent = await send_instagram_dm(page_token, sender_id, reply)

    conv = Conversation(
        tenant_id=uuid.UUID(tenant_id),
        customer_id=customer.id,
        session_id=session.id,
        platform="instagram",
        channel_type="dm",
        platform_message_id=message_id,
        message_in=message,
        message_out=reply if sent else None,
        intent=intent_result.intent,
        sentiment=intent_result.sentiment,
        is_human_takeover=False,
    )
    db.add(conv)

    if _is_closing_signal(message, reply if sent else None, intent_result.intent):
        session.status = "closed"
        session.closed_at = datetime.now(timezone.utc)
        logger.info("Session closed by AI signal", extra={"session_id": str(session.id)})

    await _save_system_log(
        tenant_id, "instagram_dm_reply", "success" if sent else "failed",
        {"message_id": message_id, "sent": sent}, db,
    )
    return str(customer.id)
```

- [ ] **Step 4: Jalankan test — verifikasi PASS**

```bash
cd backend && python -m pytest tests/test_engagement_service.py -v 2>&1 | tail -20
```

Expected: Semua test pass (termasuk yang lama).

- [ ] **Step 5: Commit**

```bash
cd backend && git add app/services/engagement_service.py app/services/instagram_service.py tests/test_engagement_service.py
git commit -m "feat: add process_instagram_dm to engagement_service"
```

---

## Task 3: Celery Worker — `process_instagram_event`

**Files:**
- Modify: `backend/workers/engagement_worker.py`
- Test: `backend/tests/test_engagement_worker.py`

**Interfaces:**
- Consumes: `process_instagram_dm(tenant_id, event, db)` (Task 2)
- Produces: Celery task `workers.engagement_worker.process_instagram_event`

- [ ] **Step 1: Tulis failing tests**

Tambahkan ke `backend/tests/test_engagement_worker.py` (append setelah isi yang ada):

```python
from workers.engagement_worker import process_instagram_event


def test_instagram_task_is_registered():
    from workers.celery_app import celery_app
    assert "workers.engagement_worker.process_instagram_event" in celery_app.tasks


def test_instagram_task_has_retry_config():
    task = process_instagram_event
    assert task.max_retries == 3
    assert task.retry_backoff is True


def test_process_instagram_event_dm():
    tenant_id = "tenant-ig-123"
    event = {
        "channel_type": "dm",
        "message_id": "ig-m1",
        "message": "halo kak",
        "sender_id": "igsid-u1",
    }

    with patch("workers.engagement_worker.asyncio.run") as mock_run:
        mock_run.return_value = None
        process_instagram_event(tenant_id, event)

    mock_run.assert_called_once()


def test_process_instagram_event_unknown_channel_type_does_not_crash():
    tenant_id = "tenant-ig-456"
    event = {
        "channel_type": "comment",  # belum didukung di Instagram
        "message_id": "ig-m2",
        "message": "test",
        "sender_id": "igsid-u2",
    }

    with patch("workers.engagement_worker.asyncio.run") as mock_run:
        mock_run.return_value = None
        process_instagram_event(tenant_id, event)

    # Tidak crash — cukup log warning dan selesai
    mock_run.assert_called_once()
```

- [ ] **Step 2: Jalankan test — verifikasi FAIL**

```bash
cd backend && python -m pytest tests/test_engagement_worker.py::test_instagram_task_is_registered -v 2>&1 | tail -10
```

Expected: `ImportError` atau `AssertionError` karena task belum ada.

- [ ] **Step 3: Tambahkan `process_instagram_event` ke engagement_worker.py**

Append ke `backend/workers/engagement_worker.py` setelah fungsi `process_facebook_event`:

```python
@celery_app.task(
    bind=True,
    name="workers.engagement_worker.process_instagram_event",
    queue="engagement",
    max_retries=3,
    default_retry_delay=30,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def process_instagram_event(self, tenant_id: str, event: dict) -> None:
    """
    Proses satu event Instagram DM untuk tenant.
    event["channel_type"]: "dm" (comment belum didukung)
    """
    channel_type = event.get("channel_type", "dm")

    async def _run() -> str | None:
        from sqlalchemy.pool import NullPool
        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
        from app.core.config import get_settings
        from app.services.engagement_service import process_instagram_dm

        import app.models  # noqa: F401

        _settings = get_settings()
        _engine = create_async_engine(_settings.DATABASE_URL, poolclass=NullPool)
        _Session = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)

        customer_id: str | None = None
        try:
            async with _Session() as session:
                async with session.begin():
                    if channel_type == "dm":
                        customer_id = await process_instagram_dm(tenant_id, event, session)
                    else:
                        logger.warning(
                            "Unsupported channel_type for Instagram",
                            extra={"channel_type": channel_type, "tenant_id": tenant_id},
                        )
            return customer_id
        finally:
            await _engine.dispose()

    try:
        customer_id = asyncio.run(_run())
        logger.info(
            "Instagram event processed",
            extra={"tenant_id": tenant_id, "channel_type": channel_type},
        )
        if customer_id is not None:
            from workers.lead_worker import classify_lead
            classify_lead.delay(tenant_id, customer_id)
    except Exception as exc:
        logger.error(
            "process_instagram_event failed",
            extra={"tenant_id": tenant_id, "error": str(exc)},
        )
        raise
```

- [ ] **Step 4: Jalankan test — verifikasi PASS**

```bash
cd backend && python -m pytest tests/test_engagement_worker.py -v 2>&1 | tail -15
```

Expected: Semua test pass (termasuk yang lama).

- [ ] **Step 5: Commit**

```bash
cd backend && git add workers/engagement_worker.py tests/test_engagement_worker.py
git commit -m "feat: add process_instagram_event Celery worker"
```

---

## Task 4: Webhook Endpoints — GET + POST `/webhooks/instagram`

**Files:**
- Modify: `backend/app/routers/webhooks.py`
- Test: `backend/tests/test_webhook_router.py`

**Interfaces:**
- Consumes: `process_instagram_event` Celery task (Task 3)
- Consumes: `_verify_fb_signature` (sudah ada di webhooks.py)
- Consumes: `FacebookWebhookPayload` schema (sudah ada)
- Produces:
  - `GET /webhooks/instagram` → verifikasi Meta webhook
  - `POST /webhooks/instagram?tenant_id=<uuid>` → terima event, queue ke Celery

- [ ] **Step 1: Tulis failing tests**

Tambahkan ke `backend/tests/test_webhook_router.py` (append setelah isi yang ada):

```python
def test_instagram_verify_success(client):
    settings = get_settings()
    res = client.get("/webhooks/instagram", params={
        "hub.mode": "subscribe",
        "hub.verify_token": settings.META_VERIFY_TOKEN,
        "hub.challenge": "challenge-ig-123",
    })
    assert res.status_code == 200
    assert res.text == "challenge-ig-123"


def test_instagram_verify_wrong_token_returns_403(client):
    res = client.get("/webhooks/instagram", params={
        "hub.mode": "subscribe",
        "hub.verify_token": "wrong-token",
        "hub.challenge": "challenge-xyz",
    })
    assert res.status_code == 403


def test_instagram_receive_dm_event(client):
    payload = {
        "object": "instagram",
        "entry": [{
            "id": "ig-account-123",
            "messaging": [{
                "sender": {"id": "igsid-user-1"},
                "recipient": {"id": "ig-account-123"},
                "message": {"mid": "ig-mid-abc", "text": "Halo kak stok ada?"},
            }]
        }]
    }

    with patch("app.routers.webhooks.process_instagram_event") as mock_task:
        mock_task.delay = MagicMock()
        res = client.post(
            "/webhooks/instagram",
            params={"tenant_id": "00000000-0000-0000-0000-000000000001"},
            json=payload,
        )

    assert res.status_code == 200
    assert res.json()["queued"] == 1
    mock_task.delay.assert_called_once()


def test_instagram_receive_ignores_echo_message(client):
    payload = {
        "object": "instagram",
        "entry": [{
            "id": "ig-account-123",
            "messaging": [{
                "sender": {"id": "ig-account-123"},
                "recipient": {"id": "igsid-user-1"},
                "message": {"mid": "ig-mid-echo", "text": "Echo reply", "is_echo": True},
            }]
        }]
    }

    with patch("app.routers.webhooks.process_instagram_event") as mock_task:
        mock_task.delay = MagicMock()
        res = client.post(
            "/webhooks/instagram",
            params={"tenant_id": "00000000-0000-0000-0000-000000000001"},
            json=payload,
        )

    assert res.status_code == 200
    assert res.json()["queued"] == 0
    mock_task.delay.assert_not_called()


def test_instagram_receive_ignores_non_instagram_object(client):
    payload = {"object": "page", "entry": []}

    with patch("app.routers.webhooks.process_instagram_event") as mock_task:
        mock_task.delay = MagicMock()
        res = client.post(
            "/webhooks/instagram",
            params={"tenant_id": "00000000-0000-0000-0000-000000000001"},
            json=payload,
        )

    assert res.status_code == 200
    assert res.json()["status"] == "ignored"
    mock_task.delay.assert_not_called()


def test_instagram_receive_invalid_payload_returns_400(client):
    res = client.post(
        "/webhooks/instagram",
        params={"tenant_id": "00000000-0000-0000-0000-000000000001"},
        content=b"bukan json",
        headers={"Content-Type": "application/json"},
    )
    assert res.status_code == 400
```

- [ ] **Step 2: Jalankan test — verifikasi FAIL**

```bash
cd backend && python -m pytest tests/test_webhook_router.py::test_instagram_verify_success -v 2>&1 | tail -10
```

Expected: `404 Not Found` karena endpoint belum ada.

- [ ] **Step 3: Tambahkan import dan dua endpoint ke webhooks.py**

Tambahkan import `process_instagram_event` di baris 10 (setelah import `process_facebook_event`):

```python
from workers.engagement_worker import process_facebook_event, process_instagram_event
```

Tambahkan dua endpoint baru di akhir file `backend/app/routers/webhooks.py`:

```python
@router.get("/instagram", response_class=PlainTextResponse)
async def instagram_verify(
    hub_mode: str = Query(alias="hub.mode"),
    hub_verify_token: str = Query(alias="hub.verify_token"),
    hub_challenge: str = Query(alias="hub.challenge"),
) -> str:
    """Endpoint verifikasi webhook Instagram — dipanggil sekali saat setup di Meta Console."""
    settings = get_settings()
    if hub_mode == "subscribe" and hub_verify_token == settings.META_VERIFY_TOKEN:
        logger.info("Instagram webhook verified")
        return hub_challenge
    raise HTTPException(status_code=403, detail="Verify token tidak valid.")


@router.post("/instagram")
async def instagram_receive(
    request: Request,
    tenant_id: str = Query(..., description="UUID tenant pemilik akun Instagram ini"),
) -> dict:
    """Terima event webhook Instagram (DM)."""
    settings = get_settings()
    body = await request.body()

    if settings.META_APP_SECRET:
        signature = request.headers.get("X-Hub-Signature-256")
        if not _verify_fb_signature(body, signature, settings.META_APP_SECRET):
            logger.warning(
                "Invalid Instagram webhook signature",
                extra={"tenant_id": tenant_id},
            )
            raise HTTPException(status_code=403, detail="Signature tidak valid.")

    try:
        payload = FacebookWebhookPayload.model_validate_json(body)
    except Exception:
        raise HTTPException(status_code=400, detail="Payload tidak valid.")

    if payload.object != "instagram":
        return {"status": "ignored", "reason": "object bukan instagram"}

    queued = 0
    for entry in payload.entry:
        for msg_event in entry.get("messaging", []):
            if "message" in msg_event and not msg_event["message"].get("is_echo"):
                event = {
                    "channel_type": "dm",
                    "message_id": msg_event["message"].get("mid", ""),
                    "message": msg_event["message"].get("text", ""),
                    "sender_id": msg_event.get("sender", {}).get("id", ""),
                }
                process_instagram_event.delay(tenant_id, event)
                queued += 1

    logger.info(
        "Instagram webhook received",
        extra={"tenant_id": tenant_id, "queued": queued},
    )
    return {"status": "ok", "queued": queued}
```

- [ ] **Step 4: Jalankan semua test — verifikasi PASS**

```bash
cd backend && python -m pytest tests/test_webhook_router.py tests/test_engagement_service.py tests/test_instagram_service.py tests/test_engagement_worker.py -v 2>&1 | tail -25
```

Expected: Semua test pass, tidak ada regression.

- [ ] **Step 5: Jalankan full test suite — verifikasi tidak ada regression**

```bash
cd backend && python -m pytest --tb=short 2>&1 | tail -20
```

Expected: Semua test pass.

- [ ] **Step 6: Commit**

```bash
cd backend && git add app/routers/webhooks.py tests/test_webhook_router.py
git commit -m "feat: add Instagram DM webhook endpoints GET+POST /webhooks/instagram"
```

---

## Self-Review Checklist

**Spec coverage:**
- ✓ GET /webhooks/instagram — Task 4
- ✓ POST /webhooks/instagram dengan signature verify — Task 4
- ✓ Filter `object == "instagram"` — Task 4
- ✓ Skip `is_echo: true` — Task 4
- ✓ `instagram_service.py` dengan `get_instagram_user_name` + `send_instagram_dm` — Task 1
- ✓ `_get_instagram_credential` (platform="instagram") — Task 2
- ✓ `process_instagram_dm` dengan semua shared helpers — Task 2
- ✓ Feature flag `"instagram_reply"` — Task 2
- ✓ Dedup via `platform_message_id` — Task 2
- ✓ Escalation path — Task 2
- ✓ Celery task `process_instagram_event` — Task 3
- ✓ `classify_lead.delay()` setelah proses — Task 3
- ✓ Tidak ada perubahan Facebook — confirmed (hanya append/tambah)

**Type consistency:**
- `get_instagram_user_name(page_token: str, igsid: str) -> str | None` — konsisten Task 1 → Task 2
- `send_instagram_dm(page_token: str, recipient_igsid: str, message: str) -> bool` — konsisten Task 1 → Task 2
- `process_instagram_dm(tenant_id: str, event: dict, db: AsyncSession) -> str | None` — konsisten Task 2 → Task 3
- `process_instagram_event` Celery task — konsisten Task 3 → Task 4

**Placeholders:** Tidak ada TBD/TODO.
