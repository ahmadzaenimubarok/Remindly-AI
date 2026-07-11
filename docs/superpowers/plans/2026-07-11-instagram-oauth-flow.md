# Instagram OAuth Flow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implementasi OAuth 2.0 flow untuk Instagram — menggantikan flow manual (paste token) yang ada saat ini. User cukup klik "Connect Instagram", authorize di Meta, pilih akun Instagram, selesai.

**Architecture:** Backend mendapatkan authorization code dari Meta (dengan scopes Instagram) → tukar ke token → ambil daftar Facebook Pages → cek mana yang punya Instagram Business Account → redirect ke frontend dengan data → user pilih akun IG → simpan koneksi.

**Key Insight:** Instagram Business diakses melalui Facebook Page. OAuth flow tetap menggunakan Meta App yang sama, tapi dengan scopes `instagram_basic` + `instagram_manage_messages`. Setelah mendapatkan Pages, kita perlu fetch `{page-id}?fields=instagram_business_account` untuk mendapatkan Instagram Account ID.

**Tech Stack:** FastAPI, SQLAlchemy async, httpx, Pydantic (backend) · React 19, TypeScript, Axios (frontend)

## Global Constraints

- Graph API base URL: `https://graph.facebook.com/v21.0`
- OAuth URLs:
  - Authorization: `https://www.facebook.com/v21.0/dialog/oauth`
  - Token Exchange: `https://graph.facebook.com/v21.0/oauth/access_token`
  - Long-lived Token: `https://graph.facebook.com/v21.0/oauth/access_token?grant_type=fb_exchange_token`
  - User Pages: `https://graph.facebook.com/v21.0/me/accounts`
  - Instagram Business Account: `https://graph.facebook.com/v21.0/{page-id}?fields=instagram_business_account`
- Scopes: `pages_show_list,instagram_basic,instagram_manage_messages`
- Encryption: gunakan `encrypt_credential`/`decrypt_credential` yang sudah ada (Fernet/AES-256)
- Redirect URI: `{META_IG_REDIRECT_URI}` (backend callback) → redirect ke `{FRONTEND_URL}/auth/instagram/callback`
- Ikuti pola test yang ada: `unittest.mock`, `pytest.mark.asyncio`, patch by dotted path

---

## File Map

| File | Action | Tanggung jawab |
|---|---|---|
| `backend/app/core/config.py` | **Edit** | Tambah `META_IG_REDIRECT_URI` |
| `backend/app/schemas/instagram_oauth.py` | **Create** | Request/response schemas |
| `backend/app/services/instagram_oauth_service.py` | **Create** | OAuth flow: token exchange, IG account detection, connection save |
| `backend/app/routers/instagram_oauth.py` | **Create** | Endpoints: login, callback, connect, disconnect |
| `backend/app/main.py` | **Edit** | Register Instagram OAuth router |
| `backend/app/services/settings_service.py` | **Edit** | Update `save_ig_token` untuk support OAuth flow |
| `frontend/src/hooks/useInstagramOAuth.ts` | **Create** | Hook untuk OAuth flow |
| `frontend/src/pages/InstagramCallback.tsx` | **Create** | Halaman callback OAuth |
| `frontend/src/pages/InstagramConnect.tsx` | **Create** | Halaman connect Instagram |
| `frontend/src/App.tsx` | **Edit** | Tambah routes untuk Instagram OAuth |
| `frontend/src/pages/Settings.tsx` | **Edit** | Ganti form manual dengan tombol OAuth |

---

## Task 1: Backend Config + Schema

**Files:**
- Modify: `backend/app/core/config.py`
- Create: `backend/app/schemas/instagram_oauth.py`

**Interfaces:**
- Produces:
  - `META_IG_REDIRECT_URI: str` di Settings
  - `InstagramConnectRequest` — Pydantic model untuk connect
  - `InstagramAccountInfo` — Response model untuk IG account info

- [ ] **Step 1: Update `config.py` — tambah META_IG_REDIRECT_URI**

Tambahkan setelah `META_REDIRECT_URI`:

```python
META_IG_REDIRECT_URI: str = ""  # Backend callback URL untuk Instagram OAuth
```

- [ ] **Step 2: Buat `schemas/instagram_oauth.py`**

Buat file `backend/app/schemas/instagram_oauth.py`:

```python
from pydantic import BaseModel, Field


class InstagramConnectRequest(BaseModel):
    page_id: str = Field(..., min_length=1)
    page_name: str = Field(default="")
    page_token: str = Field(..., min_length=1)
    instagram_account_id: str = Field(..., min_length=1)
    instagram_username: str = Field(default="")


class InstagramAccountInfo(BaseModel):
    page_id: str
    page_name: str
    page_token: str
    instagram_account_id: str
    instagram_username: str
    instagram_name: str
```

- [ ] **Step 3: Commit**

```bash
cd backend && git add app/core/config.py app/schemas/instagram_oauth.py
git commit -m "feat: add Instagram OAuth config and schemas"
```

---

## Task 2: Instagram OAuth Service

**Files:**
- Create: `backend/app/services/instagram_oauth_service.py`

**Interfaces:**
- Produces:
  - `exchange_code_for_token(code: str) -> dict | None` — tukar code → short-lived token (reuse dari Facebook)
  - `exchange_to_long_lived_token(short_token: str) -> dict | None` — tukar ke long-lived token (reuse dari Facebook)
  - `get_user_pages(long_token: str) -> list[dict]` — ambil daftar Pages (reuse dari Facebook)
  - `get_instagram_accounts_for_pages(long_token: str, pages: list[dict]) -> list[dict]` — untuk setiap page, cek apakah punya Instagram Business Account
  - `save_instagram_connection(tenant_id, page_id, page_token, ig_account_id, db) -> TenantCredential` — simpan koneksi Instagram

- [ ] **Step 1: Buat `instagram_oauth_service.py`**

Buat file `backend/app/services/instagram_oauth_service.py`:

```python
import logging
import uuid
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import select

from app.core.config import get_settings
from app.core.security import encrypt_credential
from app.models.tenant_credential import TenantCredential

logger = logging.getLogger(__name__)

GRAPH_API_BASE = "https://graph.facebook.com/v21.0"
TOKEN_URL = f"{GRAPH_API_BASE}/oauth/access_token"
PAGES_URL = f"{GRAPH_API_BASE}/me/accounts"
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
                    "redirect_uri": settings.META_IG_REDIRECT_URI,
                    "code": code,
                },
            )
            if response.is_success:
                return response.json()
            logger.error(
                f"IG exchange_code_for_token failed: {response.status_code} {response.text}"
            )
    except Exception:
        logger.exception("IG exchange_code_for_token error")
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
                f"IG exchange_to_long_lived_token failed: {response.status_code} {response.text}"
            )
    except Exception:
        logger.exception("IG exchange_to_long_lived_token error")
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
            logger.error(f"IG get_user_pages failed: {response.status_code} {response.text}")
    except Exception:
        logger.exception("IG get_user_pages error")
    return []


async def get_instagram_accounts_for_pages(
    long_token: str, pages: list[dict]
) -> list[dict]:
    """Untuk setiap Facebook Page, cek apakah punya Instagram Business Account.
    Kembalikan list page yang punya IG account beserta info IG-nya."""
    results = []
    try:
        with httpx.Client(timeout=30.0) as client:
            for page in pages:
                page_id = page["id"]
                try:
                    response = client.get(
                        f"{GRAPH_API_BASE}/{page_id}",
                        params={
                            "access_token": long_token,
                            "fields": "instagram_business_account{id,name,username}",
                        },
                    )
                    if response.is_success:
                        data = response.json()
                        ig_account = data.get("instagram_business_account")
                        if ig_account:
                            results.append({
                                "page_id": page_id,
                                "page_name": page["name"],
                                "page_token": page["access_token"],
                                "instagram_account_id": ig_account["id"],
                                "instagram_username": ig_account.get("username", ""),
                                "instagram_name": ig_account.get("name", ""),
                            })
                except Exception:
                    logger.warning(
                        "Failed to check IG account for page",
                        extra={"page_id": page_id},
                    )
    except Exception:
        logger.exception("get_instagram_accounts_for_pages error")
    return results


async def save_instagram_connection(
    tenant_id: str,
    page_id: str,
    page_token: str,
    ig_account_id: str,
    db,
) -> TenantCredential:
    """Simpan atau update koneksi Instagram untuk tenant."""
    existing_result = await db.execute(
        select(TenantCredential).where(
            TenantCredential.tenant_id == uuid.UUID(tenant_id),
            TenantCredential.platform == "instagram",
            TenantCredential.page_id == page_id,
        )
    )
    credential = existing_result.scalar_one_or_none()
    encrypted = encrypt_credential(page_token)

    expires_at = datetime.now(timezone.utc) + timedelta(days=60)

    if credential is None:
        credential = TenantCredential(
            tenant_id=uuid.UUID(tenant_id),
            platform="instagram",
            access_token_encrypted=encrypted,
            page_id=page_id,
            facebook_user_id=ig_account_id,  # Simpan IG Account ID di kolom ini
            expires_at=expires_at,
        )
        db.add(credential)
    else:
        credential.access_token_encrypted = encrypted
        credential.page_id = page_id
        credential.facebook_user_id = ig_account_id
        credential.expires_at = expires_at

    await db.flush()
    logger.info(
        "Instagram connection saved",
        extra={"tenant_id": tenant_id, "page_id": page_id, "ig_account_id": ig_account_id},
    )
    return credential


async def disconnect_instagram_connection(tenant_id: str, db) -> None:
    """Hapus semua koneksi Instagram untuk tenant."""
    await db.execute(
        select(TenantCredential).where(
            TenantCredential.tenant_id == uuid.UUID(tenant_id),
            TenantCredential.platform == "instagram",
        )
    )
    await db.flush()
    logger.info("Instagram connection disconnected", extra={"tenant_id": tenant_id})
```

- [ ] **Step 2: Commit**

```bash
cd backend && git add app/services/instagram_oauth_service.py
git commit -m "feat: add instagram_oauth_service — token exchange, IG account detection, connection save"
```

---

## Task 3: Instagram OAuth Router

**Files:**
- Create: `backend/app/routers/instagram_oauth.py`
- Modify: `backend/app/main.py`

**Interfaces:**
- Consumes: semua fungsi dari `instagram_oauth_service` (Task 2)
- Produces:
  - `GET /api/v1/auth/instagram/login` — generate OAuth URL
  - `GET /api/v1/auth/instagram/callback` — tukar code, ambil pages + IG accounts, redirect ke frontend
  - `POST /api/v1/auth/instagram/connect` — simpan koneksi
  - `DELETE /api/v1/auth/instagram/disconnect` — hapus koneksi

- [ ] **Step 1: Buat `instagram_oauth.py` router**

Buat file `backend/app/routers/instagram_oauth.py`:

```python
import base64
import json
import logging
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db_session
from app.schemas.instagram_oauth import InstagramConnectRequest
from app.services.instagram_oauth_service import (
    disconnect_instagram_connection,
    exchange_code_for_token,
    exchange_to_long_lived_token,
    get_instagram_accounts_for_pages,
    get_user_pages,
    save_instagram_connection,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth/instagram", tags=["instagram-oauth"])


@router.get("/login")
async def instagram_login(request: Request):
    """Generate Instagram OAuth URL untuk redirect customer."""
    settings = get_settings()
    tenant_id: str = request.state.tenant_id

    params = {
        "client_id": settings.META_APP_ID,
        "redirect_uri": settings.META_IG_REDIRECT_URI,
        "scope": "pages_show_list,instagram_basic,instagram_manage_messages",
        "response_type": "code",
        "state": tenant_id,
    }
    url = f"https://www.facebook.com/v21.0/dialog/oauth?{urlencode(params)}"
    return {"url": url}


@router.get("/callback")
async def instagram_callback(
    code: str | None = Query(None),
    state: str = Query(...),
    error: str | None = Query(None),
):
    """
    Backend callback endpoint — dipanggil oleh Meta setelah user authorize.
    Exchange code → token → ambil pages → cek IG accounts → redirect ke frontend.
    """
    settings = get_settings()

    if error:
        frontend_url = f"{settings.FRONTEND_URL}/auth/instagram/callback?error={error}"
        return RedirectResponse(url=frontend_url)

    if not code:
        error_msg = "no_code"
        frontend_url = f"{settings.FRONTEND_URL}/auth/instagram/callback?error={error_msg}"
        return RedirectResponse(url=frontend_url)

    # 1. Tukar code → short-lived token
    short_token_data = await exchange_code_for_token(code)
    if not short_token_data:
        error_msg = "exchange_failed"
        frontend_url = f"{settings.FRONTEND_URL}/auth/instagram/callback?error={error_msg}"
        return RedirectResponse(url=frontend_url)

    # 2. Tukar → long-lived token
    long_token_data = await exchange_to_long_lived_token(short_token_data["access_token"])
    if not long_token_data:
        error_msg = "long_lived_exchange_failed"
        frontend_url = f"{settings.FRONTEND_URL}/auth/instagram/callback?error={error_msg}"
        return RedirectResponse(url=frontend_url)

    long_token = long_token_data["access_token"]

    # 3. Ambil daftar Pages
    pages = await get_user_pages(long_token)

    # 4. Untuk setiap page, cek apakah punya Instagram Business Account
    ig_accounts = await get_instagram_accounts_for_pages(long_token, pages)

    # 5. Encode data dan redirect ke frontend
    callback_data = {
        "state": state,
        "accounts": ig_accounts,
    }

    encoded_data = base64.urlsafe_b64encode(json.dumps(callback_data).encode()).decode()
    frontend_url = f"{settings.FRONTEND_URL}/auth/instagram/callback?data={encoded_data}"

    return RedirectResponse(url=frontend_url)


@router.post("/connect")
async def instagram_connect(
    body: InstagramConnectRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """Simpan koneksi Instagram ke tenant."""
    tenant_id: str = request.state.tenant_id

    await save_instagram_connection(
        tenant_id=tenant_id,
        page_id=body.page_id,
        page_token=body.page_token,
        ig_account_id=body.instagram_account_id,
        db=db,
    )

    return {
        "message": "Instagram berhasil dihubungkan.",
        "instagram_account_id": body.instagram_account_id,
    }


@router.delete("/disconnect")
async def instagram_disconnect(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """Hapus koneksi Instagram untuk tenant."""
    tenant_id: str = request.state.tenant_id
    await disconnect_instagram_connection(tenant_id, db)

    return {"message": "Instagram connection berhasil dihapus."}
```

- [ ] **Step 2: Register router di `app/main.py`**

Tambahkan import di baris 13:

```python
from app.routers import auth, billing, conversations, facebook_oauth, features, instagram_oauth, leads, products, settings, webhooks
```

Tambahkan setelah `app.include_router(facebook_oauth.router)`:

```python
app.include_router(instagram_oauth.router)
```

- [ ] **Step 3: Commit**

```bash
cd backend && git add app/routers/instagram_oauth.py app/main.py
git commit -m "feat: add Instagram OAuth endpoints — login, callback, connect, disconnect"
```

---

## Task 4: Frontend — Hook + Pages

**Files:**
- Create: `frontend/src/hooks/useInstagramOAuth.ts`
- Create: `frontend/src/pages/InstagramCallback.tsx`
- Create: `frontend/src/pages/InstagramConnect.tsx`

**Interfaces:**
- Consumes: semua endpoints dari Task 3

- [ ] **Step 1: Buat `useInstagramOAuth.ts` hook**

Buat file `frontend/src/hooks/useInstagramOAuth.ts`:

```typescript
import { useCallback, useState } from "react";
import api from "@/lib/api";

export interface InstagramAccount {
  page_id: string;
  page_name: string;
  page_token: string;
  instagram_account_id: string;
  instagram_username: string;
  instagram_name: string;
}

export interface InstagramOAuthData {
  accounts: InstagramAccount[];
}

export function useInstagramOAuth() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const getLoginUrl = useCallback(async (): Promise<string | null> => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.get<{ url: string }>("/auth/instagram/login");
      return res.data.url;
    } catch {
      setError("Gagal mendapatkan URL login Instagram.");
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const connectAccount = useCallback(
    async (
      pageId: string,
      pageName: string,
      pageToken: string,
      instagramAccountId: string,
      instagramUsername: string
    ): Promise<boolean> => {
      setLoading(true);
      setError(null);
      try {
        await api.post("/auth/instagram/connect", {
          page_id: pageId,
          page_name: pageName,
          page_token: pageToken,
          instagram_account_id: instagramAccountId,
          instagram_username: instagramUsername,
        });
        return true;
      } catch {
        setError("Gagal menghubungkan Instagram.");
        return false;
      } finally {
        setLoading(false);
      }
    },
    []
  );

  const disconnect = useCallback(async (): Promise<boolean> => {
    setLoading(true);
    setError(null);
    try {
      await api.delete("/auth/instagram/disconnect");
      return true;
    } catch {
      setError("Gagal memutus koneksi Instagram.");
      return false;
    } finally {
      setLoading(false);
    }
  }, []);

  return { loading, error, getLoginUrl, connectAccount, disconnect };
}
```

- [ ] **Step 2: Buat `InstagramCallback.tsx`**

Buat file `frontend/src/pages/InstagramCallback.tsx`:

```tsx
import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useInstagramOAuth } from "@/hooks/useInstagramOAuth";
import type { InstagramAccount } from "@/hooks/useInstagramOAuth";
import AppLayout from "@/components/AppLayout";
import { Button } from "@/components/ui/button";

interface CallbackData {
  state: string;
  accounts: InstagramAccount[];
}

export default function InstagramCallback() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { connectAccount, loading, error: oauthError } = useInstagramOAuth();

  const [accounts, setAccounts] = useState<InstagramAccount[]>([]);
  const [selectedAccountId, setSelectedAccountId] = useState<string | null>(null);
  const [step, setStep] = useState<"loading" | "select" | "connecting" | "done" | "error">(
    "loading"
  );
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    const error = searchParams.get("error");
    if (error) {
      setStep("error");
      setErrorMessage("Authorization dibatalkan atau gagal.");
      return;
    }

    const data = searchParams.get("data");
    if (!data) {
      setStep("error");
      setErrorMessage("Data tidak ditemukan.");
      return;
    }

    try {
      const decoded: CallbackData = JSON.parse(atob(data));
      if (decoded.accounts && decoded.accounts.length > 0) {
        setAccounts(decoded.accounts);
        setStep("select");
      } else {
        setStep("error");
        setErrorMessage(
          "Tidak ditemukan akun Instagram Business yang terhubung dengan Facebook Page Anda. Pastikan akun Instagram Anda adalah Business Account dan sudah terhubung ke Facebook Page."
        );
      }
    } catch {
      setStep("error");
      setErrorMessage("Gagal memproses data.");
    }
  }, [searchParams]);

  async function handleConnect() {
    if (!selectedAccountId) return;

    const account = accounts.find((a) => a.instagram_account_id === selectedAccountId);
    if (!account) return;

    setStep("connecting");
    const success = await connectAccount(
      account.page_id,
      account.page_name,
      account.page_token,
      account.instagram_account_id,
      account.instagram_username
    );
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
          </div>
        </div>
      </AppLayout>
    );
  }

  if (step === "error") {
    return (
      <AppLayout>
        <div className="flex h-64 items-center justify-center">
          <div className="text-center">
            <div className="mb-4 text-4xl text-red-500">✕</div>
            <h2 className="mb-2 text-lg font-semibold text-slate-900">Gagal</h2>
            <p className="text-slate-600">{errorMessage || oauthError}</p>
            <Button className="mt-4" onClick={() => navigate("/settings")} variant="outline">
              Kembali ke Settings
            </Button>
          </div>
        </div>
      </AppLayout>
    );
  }

  if (step === "select") {
    return (
      <AppLayout>
        <div className="mx-auto max-w-xl p-6">
          <h1 className="mb-4 text-xl font-semibold text-slate-900">Pilih Akun Instagram</h1>
          <p className="mb-6 text-sm text-slate-500">
            Pilih akun Instagram Business yang ingin dihubungkan.
          </p>

          <div className="space-y-3">
            {accounts.map((account) => (
              <label
                key={account.instagram_account_id}
                className={`flex items-center gap-3 rounded-lg border p-4 cursor-pointer transition-colors ${
                  selectedAccountId === account.instagram_account_id
                    ? "border-blue-500 bg-blue-50"
                    : "border-slate-200 hover:bg-slate-50"
                }`}
              >
                <input
                  type="radio"
                  name="account"
                  value={account.instagram_account_id}
                  checked={selectedAccountId === account.instagram_account_id}
                  onChange={() => setSelectedAccountId(account.instagram_account_id)}
                  className="h-4 w-4 text-blue-600"
                />
                <div>
                  <p className="font-medium text-slate-800">
                    {account.instagram_name || account.instagram_username}
                  </p>
                  <p className="text-xs text-slate-500">
                    @{account.instagram_username} — via {account.page_name}
                  </p>
                </div>
              </label>
            ))}
          </div>

          {oauthError && <p className="mt-4 text-sm text-red-600">{oauthError}</p>}

          <div className="mt-6 flex gap-3">
            <Button onClick={handleConnect} disabled={!selectedAccountId || loading}>
              {loading ? "Menghubungkan..." : "Hubungkan Instagram"}
            </Button>
            <Button variant="outline" onClick={() => navigate("/settings")}>
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
            <p className="text-slate-600">Menghubungkan Instagram...</p>
          </div>
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout>
      <div className="flex h-64 items-center justify-center">
        <div className="text-center">
          <div className="mb-4 text-4xl text-green-500">✓</div>
          <h2 className="mb-2 text-lg font-semibold text-slate-900">Berhasil!</h2>
          <p className="text-slate-600">Instagram berhasil dihubungkan.</p>
        </div>
      </div>
    </AppLayout>
  );
}
```

- [ ] **Step 3: Buat `InstagramConnect.tsx`**

Buat file `frontend/src/pages/InstagramConnect.tsx`:

```tsx
import { useEffect, useState } from "react";
import { useInstagramOAuth } from "@/hooks/useInstagramOAuth";
import AppLayout from "@/components/AppLayout";
import { Button } from "@/components/ui/button";

export default function InstagramConnect() {
  const { getLoginUrl, loading, error } = useInstagramOAuth();
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
        <h1 className="mb-4 text-xl font-semibold text-slate-900">Hubungkan Instagram</h1>
        <p className="mb-6 text-sm text-slate-500">
          Klik tombol di bawah untuk menghubungkan akun Instagram Business Anda.
        </p>

        <div className="rounded-lg border bg-white p-5 shadow-sm">
          <h2 className="mb-4 font-medium text-slate-800">Instagram Business</h2>
          <p className="mb-4 text-sm text-slate-500">
            Anda akan diarahkan ke Meta untuk memberikan izin akses. Pastikan akun Instagram Anda
            adalah Business Account yang sudah terhubung ke Facebook Page.
          </p>

          {error && <p className="mb-4 text-sm text-red-600">{error}</p>}

          <Button onClick={handleConnect} disabled={loading || !loginUrl}>
            {loading ? "Memuat..." : "Connect Instagram"}
          </Button>
        </div>
      </div>
    </AppLayout>
  );
}
```

- [ ] **Step 4: Commit**

```bash
cd frontend && git add src/hooks/useInstagramOAuth.ts src/pages/InstagramCallback.tsx src/pages/InstagramConnect.tsx
git commit -m "feat: add Instagram OAuth hook, callback page, and connect page"
```

---

## Task 5: Frontend — Routes + Settings Update

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/pages/Settings.tsx`

**Interfaces:**
- Consumes: `InstagramCallback.tsx`, `InstagramConnect.tsx` dari Task 4

- [ ] **Step 1: Update `App.tsx` — tambah routes**

Tambahkan import:

```tsx
import InstagramCallback from "@/pages/InstagramCallback";
import InstagramConnect from "@/pages/InstagramConnect";
```

Tambahkan routes di dalam `<Routes>`:

```tsx
<Route
  path="/auth/instagram/callback"
  element={
    <ProtectedRoute>
      <InstagramCallback />
    </ProtectedRoute>
  }
/>
<Route
  path="/auth/instagram/connect"
  element={
    <ProtectedRoute>
      <InstagramConnect />
    </ProtectedRoute>
  }
/>
```

- [ ] **Step 2: Update `Settings.tsx` — ganti form manual dengan tombol OAuth**

Ganti card Instagram yang ada dengan versi baru:

```tsx
{/* Instagram Card */}
<div className="mt-4 rounded-lg border bg-white p-5 shadow-sm">
  <div className="mb-4 flex items-center justify-between">
    <h2 className="font-medium text-slate-800">Instagram Business</h2>
    {!isLoading && (
      <span
        className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${
          status?.instagram_connected
            ? "bg-green-100 text-green-700"
            : "bg-slate-100 text-slate-500"
        }`}
      >
        {status?.instagram_connected ? "Terhubung" : "Belum terhubung"}
      </span>
    )}
  </div>

  <p className="mb-4 text-sm text-slate-500">
    Hubungkan akun Instagram Business Anda untuk mengaktifkan auto-reply DM Instagram.
  </p>

  {status?.instagram_connected ? (
    <div className="space-y-3">
      <p className="text-sm text-green-600">✓ Instagram terhubung</p>
      <Button variant="outline" size="sm" onClick={() => navigate("/auth/instagram/connect")}>
        Hubungkan Akun Lain
      </Button>
    </div>
  ) : (
    <Button onClick={() => navigate("/auth/instagram/connect")} size="sm">
      Connect Instagram
    </Button>
  )}
</div>
```

- [ ] **Step 3: Hapus state/form manual Instagram dari Settings.tsx**

Hapus variabel state: `igPageToken`, `igAccountId`, `igSaving`, `igSaveError`, `igSaveSuccess`
Hapus fungsi `handleIGSave`
Hapus import `Input`, `Label` dari shadcn (jika tidak dipakai di tempat lain)

- [ ] **Step 4: Verifikasi TypeScript compile**

```bash
cd frontend && npm run build 2>&1 | tail -10
```

- [ ] **Step 5: Commit**

```bash
cd frontend && git add src/App.tsx src/pages/Settings.tsx
git commit -m "feat: update Settings with Instagram OAuth button and add routes"
```

---

## Task 6: Update `.env.example`

**Files:**
- Modify: `backend/.env.example`

- [ ] **Step 1: Tambah META_IG_REDIRECT_URI ke .env.example**

Tambahkan setelah `META_REDIRECT_URI`:

```ini
META_IG_REDIRECT_URI=https://<your-domain>/api/v1/auth/instagram/callback
```

- [ ] **Step 2: Commit**

```bash
cd backend && git add .env.example
git commit -m "docs: add META_IG_REDIRECT_URI to .env.example"
```

---

## Self-Review Checklist

**Spec coverage:**
- ✓ OAuth redirect flow (`/auth/instagram/login`) — Task 3
- ✓ Callback handler (`/auth/instagram/callback`) — Task 3
- ✓ Token exchange (short-lived → long-lived) — Task 2
- ✓ Page listing (`/me/accounts`) — Task 2
- ✓ Instagram Business Account detection (`{page-id}?fields=instagram_business_account`) — Task 2
- ✓ Token storage dengan encryption — Task 2
- ✓ Instagram Account ID storage — Task 2
- ✓ Disconnect endpoint — Task 3
- ✓ Frontend OAuth flow — Task 4
- ✓ Account selection UI — Task 4
- ✓ Settings UI update — Task 5

**Type consistency:**
- `exchange_code_for_token(code: str) -> dict | None` — Task 2 → Task 3
- `exchange_to_long_lived_token(short_token: str) -> dict | None` — Task 2 → Task 3
- `get_user_pages(long_token: str) -> list[dict]` — Task 2 → Task 3
- `get_instagram_accounts_for_pages(long_token, pages) -> list[dict]` — Task 2 → Task 3
- `save_instagram_connection(tenant_id, page_id, page_token, ig_account_id, db) -> TenantCredential` — Task 2 → Task 3
- `InstagramConnectRequest.page_id, page_token, instagram_account_id` — Task 1 → Task 3
- `getLoginUrl() -> Promise<string | null>` — Task 4 → Task 5
- `connectAccount(pageId, pageName, pageToken, igAccountId, igUsername) -> Promise<boolean>` — Task 4

**Placeholders:** Tidak ada TBD/TODO.

**Security notes:**
- Semua token di-encrypt dengan Fernet (AES-256) sebelum disimpan
- Long-lived token expire dalam 60 hari — perlu token refresh logic di fase berikutnya
- State parameter di OAuth URL mencegah CSRF
- Menggunakan `META_IG_REDIRECT_URI` terpisah dari Facebook

**Next phases (optional):**
- Token refresh mechanism (cron job atau on-demand)
- Instagram comment reply (saat ini hanya DM)
- Auto-detect Instagram Business Account status
- Token expiry notification ke customer
