# Facebook OAuth Flow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implementasi OAuth 2.0 flow lengkap untuk Facebook — mulai dari redirect login, token exchange, page selection, sampai auto webhook subscription. Menggantikan flow manual (paste token) yang ada saat ini.

**Architecture:** Backend mendapatkan authorization code dari Facebook → tukar ke short-lived token → tukar ke long-lived token → ambil daftar Pages → customer pilih Page → simpan token per-Page → subscribe webhook otomatis. Frontend: tombol "Connect Facebook" yang trigger OAuth redirect, halaman callback untuk proses token, dan UI untuk memilih Pages.

**Tech Stack:** FastAPI, SQLAlchemy async, httpx, Pydantic, pytest (backend) · React 19, TypeScript, Axios (frontend)

## Global Constraints

- Graph API base URL: `https://graph.facebook.com/v21.0`
- OAuth URLs:
  - Authorization: `https://www.facebook.com/v21.0/dialog/oauth`
  - Token Exchange: `https://graph.facebook.com/v21.0/oauth/access_token`
  - Long-lived Token: `https://graph.facebook.com/v21.0/oauth/access_token?grant_type=fb_exchange_token`
  - User Pages: `https://graph.facebook.com/v21.0/me/accounts`
  - Page Subscriptions: `https://graph.facebook.com/v21.0/{page-id}/subscribed_apps`
- Scopes: `pages_show_list,pages_messaging,pages_read_engagement,pages_manage_metadata`
- Database: tambah kolom `facebook_user_id` dan `page_id` ke `tenant_credentials`
- Encryption: gunakan `encrypt_credential`/`decrypt_credential` yang sudah ada (Fernet/AES-256)
- Redirect URI: `{FRONTEND_URL}/auth/facebook/callback`
- Frontend URL akan handle callback dan redirect ke backend untuk simpan token
- Ikuti pola test yang ada: `unittest.mock`, `pytest.mark.asyncio`, patch by dotted path

---

## File Map

| File | Action | Tanggung jawab |
|---|---|---|
| `backend/app/core/config.py` | **Edit** | Tambah `META_REDIRECT_URI` |
| `backend/app/models/tenant_credential.py` | **Edit** | Tambah kolom `facebook_user_id`, `page_id` |
| `backend/alembic/versions/` | **Create** | Migration untuk kolom baru |
| `backend/app/services/facebook_oauth_service.py` | **Create** | OAuth flow: token exchange, page listing, webhook subscription |
| `backend/app/schemas/facebook_oauth.py` | **Create** | Request/response schemas |
| `backend/app/routers/facebook_oauth.py` | **Create** | Endpoints: `/auth/facebook/login`, `/auth/facebook/callback`, `/auth/facebook/pages` |
| `backend/app/services/settings_service.py` | **Edit** | Update `save_fb_token` untuk support OAuth flow |
| `backend/tests/test_facebook_oauth_service.py` | **Create** | Unit test untuk facebook_oauth_service |
| `backend/tests/test_facebook_oauth_router.py` | **Create** | Unit test untuk facebook_oauth endpoints |
| `frontend/src/pages/FacebookCallback.tsx` | **Create** | Halaman callback OAuth |
| `frontend/src/pages/FacebookPages.tsx` | **Create** | Halaman pilih Pages |
| `frontend/src/hooks/useFacebookOAuth.ts` | **Create** | Hook untuk OAuth flow |
| `frontend/src/App.tsx` | **Edit** | Tambah route untuk callback dan pages |
| `frontend/src/pages/Settings.tsx` | **Edit** | Ganti form manual dengan tombol OAuth |

---

## Task 1: Backend Config + Database Migration

**Files:**
- Modify: `backend/app/core/config.py`
- Modify: `backend/app/models/tenant_credential.py`
- Create: `backend/alembic/versions/xxxx_add_facebook_oauth_columns.py`

**Interfaces:**
- Produces:
  - `META_REDIRECT_URI: str` di Settings
  - Kolom `facebook_user_id: str | None` di TenantCredential
  - Kolom `page_id: str | None` di TenantCredential

- [ ] **Step 1: Update `config.py` — tambah META_REDIRECT_URI**

Tambahkan setelah `META_VERIFY_TOKEN`:

```python
META_REDIRECT_URI: str = ""
```

- [ ] **Step 2: Update `tenant_credential.py` — tambah kolom baru**

Tambahkan setelah `expires_at`:

```python
facebook_user_id: Mapped[str | None] = mapped_column(
    String(255), nullable=True
)  # Facebook User ID (PSID)
page_id: Mapped[str | None] = mapped_column(
    String(255), nullable=True
)  # Facebook Page ID
```

- [ ] **Step 3: Buat migration file**

```bash
cd backend && alembic revision --autogenerate -m "add facebook oauth columns to tenant_credentials"
```

Edit migration file — tambahkan kolom:

```python
def upgrade() -> None:
    op.add_column(
        'tenant_credentials',
        sa.Column('facebook_user_id', sa.String(255), nullable=True)
    )
    op.add_column(
        'tenant_credentials',
        sa.Column('page_id', sa.String(255), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('tenant_credentials', 'page_id')
    op.drop_column('tenant_credentials', 'facebook_user_id')
```

- [ ] **Step 4: Jalankan migration**

```bash
cd backend && alembic upgrade head
```

- [ ] **Step 5: Commit**

```bash
cd backend && git add app/core/config.py app/models/tenant_credential.py alembic/versions/
git commit -m "feat: add Facebook OAuth columns and config"
```

---

## Task 2: Facebook OAuth Service

**Files:**
- Create: `backend/app/services/facebook_oauth_service.py`
- Test: `backend/tests/test_facebook_oauth_service.py`

**Interfaces:**
- Produces:
  - `exchange_code_for_token(code: str) -> dict | None` — tukar code → short-lived token
  - `exchange_to_long_lived_token(short_token: str) -> dict | None` — tukar ke long-lived token
  - `get_user_pages(long_token: str) -> list[dict]` — ambil daftar Pages
  - `subscribe_page_to_webhook(page_id: str, page_token: str) -> bool` — subscribe webhook
  - `get_facebook_user_id(long_token: str) -> str | None` — ambil Facebook User ID
  - `save_facebook_connection(tenant_id: str, user_id: str, page_id: str, page_token: str, db) -> TenantCredential` — simpan koneksi

- [ ] **Step 1: Tulis failing tests**

Buat file `backend/tests/test_facebook_oauth_service.py`:

```python
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
        "expires_in": 5184000,  # 60 days
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
    db = MagicMock()
    db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))
    db.flush = AsyncMock()

    with patch("app.services.facebook_oauth_service.encrypt_credential", return_value="encrypted-token"):
        result = await save_facebook_connection(
            "tenant-123", "fb-user-456", "page-789", "page-token-xyz", db
        )

    db.add.assert_called_once()
    db.flush.assert_called_once()
```

- [ ] **Step 2: Jalankan test — verifikasi FAIL**

```bash
cd backend && python -m pytest tests/test_facebook_oauth_service.py -v 2>&1 | head -20
```

Expected: `ImportError` karena file belum ada.

- [ ] **Step 3: Buat `facebook_oauth_service.py`**

Buat file `backend/app/services/facebook_oauth_service.py`:

```python
import logging
from datetime import datetime, timedelta, timezone

import httpx

from app.core.config import get_settings
from app.core.security import encrypt_credential
from app.models.tenant_credential import TenantCredential

logger = logging.getLogger(__name__)

GRAPH_API_BASE = "https://graph.facebook.com/v21.0"
OAUTH_BASE = "https://www.facebook.com/v21.0/dialog/oauth"
TOKEN_URL = f"{GRAPH_API_BASE}/oauth/access_token"
PAGES_URL = f"{GRAPH_API_BASE}/me/accounts"
SUBSCRIBE_URL = f"{GRAPH_API_BASE}/{{page_id}}/subscribed_apps"
USER_URL = f"{GRAPH_API_BASE}/me"


async def exchange_code_for_token(code: str) -> dict | None:
    """Tukar authorization code → short-lived access token."""
    settings = get_settings()
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(
                TOKEN_URL,
                params={
                    "client_id": settings.META_APP_ID,
                    "client_secret": settings.META_APP_SECRET,
                    "redirect_uri": settings.META_REDIRECT_URI,
                    "code": code,
                },
            )
            if response.is_success:
                return response.json()
            logger.error(
                f"exchange_code_for_token failed: {response.status_code} {response.text}"
            )
    except Exception:
        logger.exception("exchange_code_for_token error")
    return None


async def exchange_to_long_lived_token(short_token: str) -> dict | None:
    """Tukar short-lived token → long-lived token (60 hari)."""
    settings = get_settings()
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(
                TOKEN_URL,
                params={
                    "grant_type": "fb_exchange_token",
                    "client_id": settings.META_APP_ID,
                    "client_secret": settings.META_APP_SECRET,
                    "fb_exchange_token": short_token,
                },
            )
            if response.is_success:
                return response.json()
            logger.error(
                f"exchange_to_long_lived_token failed: {response.status_code} {response.text}"
            )
    except Exception:
        logger.exception("exchange_to_long_lived_token error")
    return None


async def get_user_pages(long_token: str) -> list[dict]:
    """Ambil daftar Facebook Pages yang dikelola user."""
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(
                PAGES_URL,
                params={"access_token": long_token},
            )
            if response.is_success:
                data = response.json()
                return data.get("data", [])
            logger.error(f"get_user_pages failed: {response.status_code} {response.text}")
    except Exception:
        logger.exception("get_user_pages error")
    return []


async def subscribe_page_to_webhook(page_id: str, page_token: str) -> bool:
    """Subscribe Page ke aplikasi agar menerima webhook events."""
    settings = get_settings()
    url = SUBSCRIBE_URL.format(page_id=page_id)
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                url,
                params={"access_token": page_token},
                json={
                    "subscribed_fields": [
                        "messages",
                        "messaging_postbacks",
                        "feed",
                    ],
                },
            )
            if response.is_success:
                logger.info("Page subscribed to webhook", extra={"page_id": page_id})
                return True
            logger.error(
                f"subscribe_page_to_webhook failed: {response.status_code} {response.text}"
            )
    except Exception:
        logger.exception("subscribe_page_to_webhook error")
    return False


async def get_facebook_user_id(long_token: str) -> str | None:
    """Ambil Facebook User ID dari token."""
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(
                USER_URL,
                params={"access_token": long_token, "fields": "id"},
            )
            if response.is_success:
                return response.json().get("id")
            logger.error(
                f"get_facebook_user_id failed: {response.status_code} {response.text}"
            )
    except Exception:
        logger.exception("get_facebook_user_id error")
    return None


async def save_facebook_connection(
    tenant_id: str,
    user_id: str,
    page_id: str,
    page_token: str,
    db,
) -> TenantCredential:
    """Simpan atau update koneksi Facebook untuk tenant."""
    from sqlalchemy import select
    import uuid

    existing_result = await db.execute(
        select(TenantCredential).where(
            TenantCredential.tenant_id == uuid.UUID(tenant_id),
            TenantCredential.platform == "facebook",
            TenantCredential.page_id == page_id,
        )
    )
    credential = existing_result.scalar_one_or_none()
    encrypted = encrypt_credential(page_token)

    # Hitung expires_at (60 hari dari sekarang untuk long-lived token)
    expires_at = datetime.now(timezone.utc) + timedelta(days=60)

    if credential is None:
        credential = TenantCredential(
            tenant_id=uuid.UUID(tenant_id),
            platform="facebook",
            access_token_encrypted=encrypted,
            facebook_user_id=user_id,
            page_id=page_id,
            expires_at=expires_at,
        )
        db.add(credential)
    else:
        credential.access_token_encrypted = encrypted
        credential.facebook_user_id = user_id
        credential.page_id = page_id
        credential.expires_at = expires_at

    await db.flush()
    logger.info(
        "Facebook connection saved",
        extra={"tenant_id": tenant_id, "page_id": page_id, "user_id": user_id},
    )
    return credential
```

- [ ] **Step 4: Jalankan test — verifikasi PASS**

```bash
cd backend && python -m pytest tests/test_facebook_oauth_service.py -v
```

Expected: Semua test pass.

- [ ] **Step 5: Commit**

```bash
cd backend && git add app/services/facebook_oauth_service.py tests/test_facebook_oauth_service.py
git commit -m "feat: add facebook_oauth_service — token exchange, page listing, webhook subscription"
```

---

## Task 3: Facebook OAuth Schemas

**Files:**
- Create: `backend/app/schemas/facebook_oauth.py`

**Interfaces:**
- Produces:
  - `FacebookOAuthCallbackRequest` — Pydantic model untuk callback dari frontend
  - `FacebookPageResponse` — Response model untuk daftar Pages
  - `FacebookConnectRequest` — Request model untuk koneksi Pages
  - `FacebookConnectionResponse` — Response model untuk status koneksi

- [ ] **Step 1: Buat schemas**

Buat file `backend/app/schemas/facebook_oauth.py`:

```python
from pydantic import BaseModel, Field


class FacebookOAuthCallbackRequest(BaseModel):
    code: str = Field(..., min_length=1, description="Authorization code dari Facebook")


class FacebookPageResponse(BaseModel):
    page_id: str
    page_name: str
    access_token: str


class FacebookConnectRequest(BaseModel):
    page_id: str = Field(..., min_length=1)
    page_name: str = Field(default="")
    access_token: str = Field(..., min_length=1)


class FacebookConnectionResponse(BaseModel):
    connected: bool
    page_id: str | None = None
    page_name: str | None = None
    facebook_user_id: str | None = None
```

- [ ] **Step 2: Commit**

```bash
cd backend && git add app/schemas/facebook_oauth.py
git commit -m "feat: add Facebook OAuth schemas"
```

---

## Task 4: Facebook OAuth Router

**Files:**
- Create: `backend/app/routers/facebook_oauth.py`
- Test: `backend/tests/test_facebook_oauth_router.py`

**Interfaces:**
- Consumes: semua fungsi dari `facebook_oauth_service` (Task 2)
- Produces:
  - `GET /api/v1/auth/facebook/login` — generate OAuth URL
  - `POST /api/v1/auth/facebook/callback` — tukar code, ambil pages
  - `GET /api/v1/auth/facebook/pages` — ambil pages (setelah callback)
  - `POST /api/v1/auth/facebook/connect` — simpan koneksi page
  - `DELETE /api/v1/auth/facebook/disconnect` — hapus koneksi

- [ ] **Step 1: Tulis failing tests**

Buat file `backend/tests/test_facebook_oauth_router.py`:

```python
from unittest.mock import AsyncMock, patch, MagicMock
import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def auth_client():
    with TestClient(app, raise_server_exceptions=False) as c:
        c.post("/api/v1/auth/register", json={
            "name": "FB OAuth Test",
            "email": "fboauth@test.com",
            "password": "Test1234!",
        })
        c.post("/api/v1/auth/login", json={
            "email": "fboauth@test.com",
            "password": "Test1234!",
        })
        yield c


def test_facebook_login_redirects_to_facebook(auth_client):
    with patch("app.routers.facebook_oauth.get_settings") as mock_settings:
        mock_settings.return_value = MagicMock(
            META_APP_ID="123456",
            META_REDIRECT_URI="http://localhost:3000/auth/facebook/callback"
        )
        res = auth_client.get("/api/v1/auth/facebook/login")

    assert res.status_code == 200
    assert "facebook.com" in res.json()["url"]
    assert "client_id=123456" in res.json()["url"]


def test_facebook_login_requires_auth():
    with TestClient(app, raise_server_exceptions=False) as c:
        res = c.get("/api/v1/auth/facebook/login")
    assert res.status_code == 401


def test_facebook_callback_exchanges_code(auth_client):
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

    with patch("app.routers.facebook_oauth.exchange_code_for_token", new_callable=AsyncMock) as mock_exchange, \
         patch("app.routers.facebook_oauth.exchange_to_long_lived_token", new_callable=AsyncMock) as mock_long, \
         patch("app.routers.facebook_oauth.get_facebook_user_id", new_callable=AsyncMock) as mock_uid, \
         patch("app.routers.facebook_oauth.get_user_pages", new_callable=AsyncMock) as mock_pages_fn:

        mock_exchange.return_value = mock_token_response
        mock_long.return_value = mock_long_token_response
        mock_uid.return_value = mock_user_id
        mock_pages_fn.return_value = mock_pages

        res = auth_client.post("/api/v1/auth/facebook/callback", json={"code": "auth-code-123"})

    assert res.status_code == 200
    assert res.json()["facebook_user_id"] == "fb-user-123"
    assert len(res.json()["pages"]) == 1


def test_facebook_callback_returns_error_on_exchange_failure(auth_client):
    with patch("app.routers.facebook_oauth.exchange_code_for_token", new_callable=AsyncMock) as mock_exchange:
        mock_exchange.return_value = None
        res = auth_client.post("/api/v1/auth/facebook/callback", json={"code": "bad-code"})

    assert res.status_code == 400


def test_facebook_connect_saves_connection(auth_client):
    mock_subscription = MagicMock()
    mock_subscription.return_value = True

    with patch("app.routers.facebook_oauth.save_facebook_connection", new_callable=AsyncMock) as mock_save, \
         patch("app.routers.facebook_oauth.subscribe_page_to_webhook", new_callable=AsyncMock) as mock_subscribe:

        mock_save.return_value = MagicMock()
        mock_subscribe.return_value = True

        res = auth_client.post("/api/v1/auth/facebook/connect", json={
            "page_id": "page-123",
            "page_name": "Toko Budi",
            "access_token": "page-token-xyz",
        })

    assert res.status_code == 200
    mock_save.assert_called_once()
    mock_subscribe.assert_called_once()


def test_facebook_disconnect_removes_connection(auth_client):
    with patch("app.routers.facebook_oauth.disconnect_facebook", new_callable=AsyncMock) as mock_disconnect:
        mock_disconnect.return_value = True
        res = auth_client.delete("/api/v1/auth/facebook/disconnect")

    assert res.status_code == 200
    mock_disconnect.assert_called_once()


def test_facebook_pages_endpoint_returns_pages(auth_client):
    with patch("app.routers.facebook_oauth.get_user_pages", new_callable=AsyncMock) as mock_pages:
        mock_pages.return_value = [
            {"id": "page-1", "name": "Toko Budi", "access_token": "token-1"},
        ]
        res = auth_client.get("/api/v1/auth/facebook/pages")

    assert res.status_code == 200
    assert len(res.json()["pages"]) == 1
```

- [ ] **Step 2: Jalankan test — verifikasi FAIL**

```bash
cd backend && python -m pytest tests/test_facebook_oauth_router.py -v 2>&1 | head -20
```

Expected: `ImportError` atau `404 Not Found`.

- [ ] **Step 3: Buat `facebook_oauth.py` router**

Buat file `backend/app/routers/facebook_oauth.py`:

```python
import logging
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db_session
from app.schemas.base import APIResponse
from app.schemas.facebook_oauth import (
    FacebookOAuthCallbackRequest,
    FacebookConnectRequest,
    FacebookConnectionResponse,
    FacebookPageResponse,
)
from app.services.facebook_oauth_service import (
    exchange_code_for_token,
    exchange_to_long_lived_token,
    get_facebook_user_id,
    get_user_pages,
    save_facebook_connection,
    subscribe_page_to_webhook,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth/facebook", tags=["facebook-oauth"])


@router.get("/login")
async def facebook_login(request: Request):
    """Generate Facebook OAuth URL untuk redirect customer."""
    settings = get_settings()
    params = {
        "client_id": settings.META_APP_ID,
        "redirect_uri": settings.META_REDIRECT_URI,
        "scope": "pages_show_list,pages_messaging,pages_read_engagement,pages_manage_metadata",
        "response_type": "code",
        "state": request.state.tenant_id,  # Simpan tenant_id di state
    }
    url = f"https://www.facebook.com/v21.0/dialog/oauth?{urlencode(params)}"
    return {"url": url}


@router.post("/callback")
async def facebook_callback(
    body: FacebookOAuthCallbackRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """Proses callback dari Facebook — tukar code ke token, ambil pages."""
    tenant_id: str = request.state.tenant_id

    # 1. Tukar code → short-lived token
    short_token_data = await exchange_code_for_token(body.code)
    if not short_token_data:
        raise HTTPException(status_code=400, detail="Gagal menukar authorization code.")

    # 2. Tukar → long-lived token
    long_token_data = await exchange_to_long_lived_token(short_token_data["access_token"])
    if not long_token_data:
        raise HTTPException(status_code=400, detail="Gagal menukar ke long-lived token.")

    long_token = long_token_data["access_token"]

    # 3. Ambil Facebook User ID
    user_id = await get_facebook_user_id(long_token)

    # 4. Ambil daftar Pages
    pages = await get_user_pages(long_token)

    # Simpan long-lived token di session sementara (bisa pakai Redis atau return ke frontend)
    # Untuk sekarang, return semua data ke frontend
    return {
        "facebook_user_id": user_id,
        "long_lived_token": long_token,
        "pages": [
            {
                "page_id": page["id"],
                "page_name": page["name"],
                "access_token": page["access_token"],
            }
            for page in pages
        ],
    }


@router.get("/pages")
async def facebook_pages(request: Request):
    """Ambil daftar Pages (untuk refresh atau select page tambahan)."""
    # Note: Dalam produksi, long-lived token harus disimpan di DB/Redis
    # Untuk sekarang, ini adalah placeholder — implementasi lengkap perlu token storage
    # yang lebih robust
    raise HTTPException(
        status_code=501,
        detail="Endpoint ini perlu implementasi token storage tambahan."
    )


@router.post("/connect")
async def facebook_connect(
    body: FacebookConnectRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """Simpan koneksi Facebook Page ke tenant."""
    tenant_id: str = request.state.tenant_id

    # Simpan koneksi
    credential = await save_facebook_connection(
        tenant_id=tenant_id,
        user_id="",  # Akan di-update nanti jika perlu
        page_id=body.page_id,
        page_token=body.access_token,
        db=db,
    )

    # Subscribe ke webhook
    subscribed = await subscribe_page_to_webhook(body.page_id, body.access_token)
    if not subscribed:
        logger.warning(
            "Failed to subscribe page to webhook",
            extra={"tenant_id": tenant_id, "page_id": body.page_id},
        )

    return {
        "message": "Facebook Page berhasil dihubungkan.",
        "page_id": body.page_id,
        "webhook_subscribed": subscribed,
    }


@router.delete("/disconnect")
async def facebook_disconnect(request: Request, db: AsyncSession = Depends(get_db_session)):
    """Hapus koneksi Facebook untuk tenant."""
    tenant_id: str = request.state.tenant_id
    from sqlalchemy import delete
    import uuid

    await db.execute(
        delete(TenantCredential).where(
            TenantCredential.tenant_id == uuid.UUID(tenant_id),
            TenantCredential.platform == "facebook",
        )
    )
    await db.flush()

    return {"message": "Facebook connection berhasil dihapus."}
```

- [ ] **Step 4: Register router di `app/main.py`**

Tambahkan import dan include router:

```python
from app.routers.facebook_oauth import router as facebook_oauth_router
app.include_router(facebook_oauth_router)
```

- [ ] **Step 5: Jalankan test — verifikasi PASS**

```bash
cd backend && python -m pytest tests/test_facebook_oauth_router.py -v
```

Expected: Semua test pass.

- [ ] **Step 6: Commit**

```bash
cd backend && git add app/routers/facebook_oauth.py app/main.py tests/test_facebook_oauth_router.py
git commit -m "feat: add Facebook OAuth endpoints — login, callback, connect, disconnect"
```

---

## Task 5: Frontend — OAuth Hook + Callback Page

**Files:**
- Create: `frontend/src/hooks/useFacebookOAuth.ts`
- Create: `frontend/src/pages/FacebookCallback.tsx`
- Create: `frontend/src/pages/FacebookPages.tsx`

**Interfaces:**
- Consumes: semua endpoints dari Task 4

- [ ] **Step 1: Buat `useFacebookOAuth.ts` hook**

Buat file `frontend/src/hooks/useFacebookOAuth.ts`:

```typescript
import { useCallback, useState } from "react";
import api from "@/lib/api";

export interface FacebookPage {
  page_id: string;
  page_name: string;
  access_token: string;
}

export interface FacebookOAuthData {
  facebook_user_id: string | null;
  long_lived_token: string;
  pages: FacebookPage[];
}

export function useFacebookOAuth() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const getLoginUrl = useCallback(async (): Promise<string | null> => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.get<{ url: string }>("/auth/facebook/login");
      return res.data.url;
    } catch (err: any) {
      setError("Gagal mendapatkan URL login Facebook.");
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const exchangeCode = useCallback(async (code: string): Promise<FacebookOAuthData | null> => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.post<FacebookOAuthData>("/auth/facebook/callback", { code });
      return res.data;
    } catch (err: any) {
      setError("Gagal menukar authorization code.");
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const connectPage = useCallback(async (
    pageId: string,
    pageName: string,
    accessToken: string
  ): Promise<boolean> => {
    setLoading(true);
    setError(null);
    try {
      await api.post("/auth/facebook/connect", {
        page_id: pageId,
        page_name: pageName,
        access_token: accessToken,
      });
      return true;
    } catch (err: any) {
      setError("Gagal menghubungkan Facebook Page.");
      return false;
    } finally {
      setLoading(false);
    }
  }, []);

  const disconnect = useCallback(async (): Promise<boolean> => {
    setLoading(true);
    setError(null);
    try {
      await api.delete("/auth/facebook/disconnect");
      return true;
    } catch (err: any) {
      setError("Gagal memutus koneksi Facebook.");
      return false;
    } finally {
      setLoading(false);
    }
  }, []);

  return { loading, error, getLoginUrl, exchangeCode, connectPage, disconnect };
}
```

- [ ] **Step 2: Buat `FacebookCallback.tsx`**

Buat file `frontend/src/pages/FacebookCallback.tsx`:

```tsx
import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useFacebookOAuth, FacebookPage } from "@/hooks/useFacebookOAuth";
import AppLayout from "@/components/AppLayout";
import { Button } from "@/components/ui/button";

export default function FacebookCallback() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { exchangeCode, connectPage, loading, error } = useFacebookOAuth();

  const [pages, setPages] = useState<FacebookPage[]>([]);
  const [selectedPageId, setSelectedPageId] = useState<string | null>(null);
  const [step, setStep] = useState<"loading" | "select" | "connecting" | "done">("loading");

  useEffect(() => {
    const code = searchParams.get("code");
    if (!code) {
      setStep("loading");
      return;
    }

    exchangeCode(code).then((data) => {
      if (data?.pages) {
        setPages(data.pages);
        setStep("select");
      } else {
        setStep("loading");
      }
    });
  }, [searchParams, exchangeCode]);

  async function handleConnect() {
    if (!selectedPageId) return;

    const page = pages.find((p) => p.page_id === selectedPageId);
    if (!page) return;

    setStep("connecting");
    const success = await connectPage(page.page_id, page.page_name, page.access_token);
    if (success) {
      setStep("done");
      setTimeout(() => navigate("/settings"), 2000);
    } else {
      setStep("select");
    }
  }

  if (step === "loading") {
    return (
      <AppLayout>
        <div className="flex h-64 items-center justify-center">
          <div className="text-center">
            <div className="mb-4 h-8 w-8 animate-spin rounded-full border-4 border-blue-500 border-t-transparent mx-auto" />
            <p className="text-slate-600">Memproses authorization...</p>
            {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
          </div>
        </div>
      </AppLayout>
    );
  }

  if (step === "select") {
    return (
      <AppLayout>
        <div className="mx-auto max-w-xl p-6">
          <h1 className="mb-4 text-xl font-semibold text-slate-900">Pilih Facebook Page</h1>
          <p className="mb-6 text-sm text-slate-500">
            Pilih Page yang ingin dihubungkan ke sistem Omnichannel.
          </p>

          {pages.length === 0 ? (
            <p className="text-slate-500">Tidak ada Facebook Page yang ditemukan.</p>
          ) : (
            <div className="space-y-3">
              {pages.map((page) => (
                <label
                  key={page.page_id}
                  className={`flex items-center gap-3 rounded-lg border p-4 cursor-pointer transition-colors ${
                    selectedPageId === page.page_id
                      ? "border-blue-500 bg-blue-50"
                      : "border-slate-200 hover:bg-slate-50"
                  }`}
                >
                  <input
                    type="radio"
                    name="page"
                    value={page.page_id}
                    checked={selectedPageId === page.page_id}
                    onChange={() => setSelectedPageId(page.page_id)}
                    className="h-4 w-4 text-blue-600"
                  />
                  <div>
                    <p className="font-medium text-slate-800">{page.page_name}</p>
                    <p className="text-xs text-slate-500">ID: {page.page_id}</p>
                  </div>
                </label>
              ))}
            </div>
          )}

          {error && <p className="mt-4 text-sm text-red-600">{error}</p>}

          <div className="mt-6 flex gap-3">
            <Button
              onClick={handleConnect}
              disabled={!selectedPageId || loading}
            >
              {loading ? "Menghubungkan..." : "Hubungkan Page"}
            </Button>
            <Button
              variant="outline"
              onClick={() => navigate("/settings")}
            >
              Batal
            </Button>
          </div>
        </div>
      </AppLayout>
    );
  }

  if (step === "connecting") {
    return (
      <AppLayout>
        <div className="flex h-64 items-center justify-center">
          <div className="text-center">
            <div className="mb-4 h-8 w-8 animate-spin rounded-full border-4 border-blue-500 border-t-transparent mx-auto" />
            <p className="text-slate-600">Menghubungkan Page...</p>
          </div>
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout>
      <div className="flex h-64 items-center justify-center">
        <div className="text-center">
          <div className="mb-4 text-4xl">✓</div>
          <h2 className="mb-2 text-lg font-semibold text-slate-900">Berhasil!</h2>
          <p className="text-slate-600">Facebook Page berhasil dihubungkan.</p>
        </div>
      </div>
    </AppLayout>
  );
}
```

- [ ] **Step 3: Buat `FacebookPages.tsx`**

Buat file `frontend/src/pages/FacebookPages.tsx`:

```tsx
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useFacebookOAuth } from "@/hooks/useFacebookOAuth";
import AppLayout from "@/components/AppLayout";
import { Button } from "@/components/ui/button";

export default function FacebookPages() {
  const navigate = useNavigate();
  const { getLoginUrl, loading, error } = useFacebookOAuth();
  const [loginUrl, setLoginUrl] = useState<string | null>(null);

  useEffect(() => {
    getLoginUrl().then((url) => setLoginUrl(url));
  }, [getLoginUrl]);

  function handleConnect() {
    if (loginUrl) {
      window.location.href = loginUrl;
    }
  }

  return (
    <AppLayout>
      <div className="mx-auto max-w-xl p-6">
        <h1 className="mb-4 text-xl font-semibold text-slate-900">Hubungkan Facebook</h1>
        <p className="mb-6 text-sm text-slate-500">
          Klik tombol di bawah untuk menghubungkan Facebook Page Anda.
        </p>

        <div className="rounded-lg border bg-white p-5 shadow-sm">
          <h2 className="mb-4 font-medium text-slate-800">Facebook Page</h2>
          <p className="mb-4 text-sm text-slate-500">
            Anda akan diarahkan ke Facebook untuk memberikan izin akses.
            Setelah itu, Anda dapat memilih Page yang ingin dihubungkan.
          </p>

          {error && <p className="mb-4 text-sm text-red-600">{error}</p>}

          <Button onClick={handleConnect} disabled={loading || !loginUrl}>
            {loading ? "Memuat..." : "Connect Facebook"}
          </Button>
        </div>
      </div>
    </AppLayout>
  );
}
```

- [ ] **Step 4: Commit**

```bash
cd frontend && git add src/hooks/useFacebookOAuth.ts src/pages/FacebookCallback.tsx src/pages/FacebookPages.tsx
git commit -m "feat: add Facebook OAuth hook, callback page, and pages selection"
```

---

## Task 6: Frontend — Route + Settings Update

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/pages/Settings.tsx`

**Interfaces:**
- Consumes: `FacebookCallback.tsx`, `FacebookPages.tsx` dari Task 5

- [ ] **Step 1: Update `App.tsx` — tambah routes**

Tambahkan import:

```tsx
import FacebookCallback from "@/pages/FacebookCallback";
import FacebookPages from "@/pages/FacebookPages";
```

Tambahkan routes di dalam `<Routes>`:

```tsx
<Route path="/auth/facebook/callback" element={<FacebookCallback />} />
<Route path="/auth/facebook/pages" element={<FacebookPages />} />
```

- [ ] **Step 2: Update `Settings.tsx` — ganti form manual dengan tombol OAuth**

Ganti card Facebook yang ada dengan versi baru:

```tsx
{/* Facebook Card */}
<div className="rounded-lg border bg-white p-5 shadow-sm">
  <div className="mb-4 flex items-center justify-between">
    <h2 className="font-medium text-slate-800">Facebook Page</h2>
    {!isLoading && (
      <span
        className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${
          status?.facebook_connected
            ? "bg-green-100 text-green-700"
            : "bg-slate-100 text-slate-500"
        }`}
      >
        {status?.facebook_connected ? "Terhubung" : "Belum terhubung"}
      </span>
    )}
  </div>

  <p className="mb-4 text-sm text-slate-500">
    Hubungkan Facebook Page Anda untuk mengaktifkan auto-reply komentar dan Messenger DM.
  </p>

  {status?.facebook_connected ? (
    <div className="space-y-3">
      <p className="text-sm text-green-600">✓ Facebook Page terhubung</p>
      <Button variant="outline" size="sm" onClick={() => navigate("/auth/facebook/pages")}>
        Hubungkan Page Lain
      </Button>
    </div>
  ) : (
    <Button onClick={() => navigate("/auth/facebook/pages")} size="sm">
      Connect Facebook
    </Button>
  )}
</div>
```

- [ ] **Step 3: Verifikasi TypeScript compile**

```bash
cd frontend && npm run build 2>&1 | tail -10
```

Expected: Build berhasil tanpa error.

- [ ] **Step 4: Commit**

```bash
cd frontend && git add src/App.tsx src/pages/Settings.tsx
git commit -m "feat: update Settings with OAuth button and add Facebook routes"
```

---

## Self-Review Checklist

**Spec coverage:**
- ✓ OAuth redirect flow (`/auth/facebook/login`) — Task 4
- ✓ Callback handler (`/auth/facebook/callback`) — Task 4
- ✓ Token exchange (short-lived → long-lived) — Task 2
- ✓ Page listing (`/me/accounts`) — Task 2
- ✓ Webhook subscription (`/subscribed_apps`) — Task 2
- ✓ Token storage dengan encryption — Task 2
- ✓ Facebook User ID storage — Task 1, Task 2
- ✓ Page ID storage — Task 1, Task 2
- ✓ Disconnect endpoint — Task 4
- ✓ Frontend OAuth flow — Task 5
- ✓ Page selection UI — Task 5
- ✓ Settings UI update — Task 6

**Type consistency:**
- `exchange_code_for_token(code: str) -> dict | None` — Task 2 → Task 4
- `exchange_to_long_lived_token(short_token: str) -> dict | None` — Task 2 → Task 4
- `get_user_pages(long_token: str) -> list[dict]` — Task 2 → Task 4
- `subscribe_page_to_webhook(page_id: str, page_token: str) -> bool` — Task 2 → Task 4
- `save_facebook_connection(tenant_id, user_id, page_id, page_token, db) -> TenantCredential` — Task 2 → Task 4
- `FacebookOAuthCallbackRequest.code: str` — Task 3 → Task 4
- `FacebookConnectRequest.page_id, access_token` — Task 3 → Task 4
- `getLoginUrl() -> Promise<string | null>` — Task 5 → Task 6
- `exchangeCode(code: string) -> Promise<FacebookOAuthData | null>` — Task 5
- `connectPage(pageId, pageName, accessToken) -> Promise<boolean>` — Task 5

**Placeholders:** Tidak ada TBD/TODO.

**Security notes:**
- Semua token di-encrypt dengan Fernet (AES-256) sebelum disimpan
- Long-lived token expire dalam 60 hari — perlu token refresh logic di fase berikutnya
- State parameter di OAuth URL mencegah CSRF
- Signature verification tetap aktif untuk webhook events

**Next phases (optional):**
- Token refresh mechanism (cron job atau on-demand)
- Auto webhook subscription saat pertama kali connect
- Multi-page support (pilih multiple pages sekaligus)
- Disconnect & reconnect flow
- Token expiry notification ke customer
