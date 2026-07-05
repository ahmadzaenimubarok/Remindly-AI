# Software Design Document (SDD)
## AI-Powered SaaS Dashboard — Reseller Automation Platform

**Versi:** 2.7
**Tanggal:** 4 Juli 2026
**Status:** Draft

---

## 0. AI Developer Agent Instructions

> **Bagian ini wajib dibaca pertama kali sebelum menulis satu baris kode pun.**
> Dokumen ini ditulis sebagai kontrak kerja untuk AI developer agent (Claude Code, Cursor, Copilot, atau sejenisnya). Ikuti semua aturan di bagian ini secara ketat di setiap file yang kamu buat atau ubah.

---

### 0.1 Identitas Proyek

```
Nama proyek  : reseller-ai
Backend      : FastAPI (Python 3.12)
Frontend     : React 18 + Vite + Tailwind CSS + shadcn/ui
Database     : PostgreSQL 16 + pgvector
Task queue   : Celery 5 + Celery Beat
Cache/broker : Redis 7
AI provider  : OpenAI API (GPT-4o, GPT-4o-mini, DALL·E 3, text-embedding-3-small)
```

---

### 0.2 Urutan Implementasi (Jangan Dilewati)

Kerjakan dalam urutan ini. Jangan melompat ke fase berikutnya sebelum fase sekarang selesai dan tested.

```
FASE 1 — FONDASI ✅ SELESAI (2026-07-03)
  [x] Setup project structure sesuai folder tree di Bagian 14.2
  [x] Konfigurasi PostgreSQL + pgvector + Alembic migration awal
  [x] Konfigurasi Redis + Celery app
  [x] Implementasi core/feature_flags.py (WAJIB ada sebelum engine apapun)
  [x] Implementasi middleware/error_handler.py (WAJIB ada sebelum router apapun)
  [x] Implementasi middleware/tenant_context.py
  [x] Auth: register, login, JWT issue & refresh
  [x] Tenant provisioning: buat workspace saat register

FASE 2 — ENGINE DASAR ✅ SELESAI (2026-07-04)
  [x] Engagement Engine: webhook receiver + intent classifier + auto-reply
  [x] FeatureGate component di frontend
  [x] Dashboard: Inbox page (percakapan + human override)
  Catatan:
  - Messenger DM reply: end-to-end verified ✅
  - Comment reply: kode siap, webhook trigger menunggu Meta App Review (Live mode)
  - Eskalasi human takeover: berfungsi via intent komplain + sentiment negatif
  - Token FB disimpan terenkripsi di tabel tenant_credentials (Fernet)
  - Celery worker wajib dijalankan dengan -Q celery,engagement,discovery,content,conversion
  - facebook_service.py menggunakan httpx.Client (sync) bukan AsyncClient — menghindari event loop conflict di Celery fork worker

FASE 3 — LEAD INTELLIGENCE
  [ ] Lead classification: hot / warm / cold dari percakapan masuk
  [ ] Dashboard: Leads page (daftar lead + status klasifikasi + filter)

FASE 4 — SAAS LAYER
  [ ] Subscription & billing (Midtrans/Stripe webhook)
  [ ] Usage metering + quota enforcement
  [ ] Super Admin panel
```

---

### 0.3 Aturan Wajib — Tidak Boleh Dilanggar

Setiap aturan di bawah ini berlaku di **semua file, semua waktu**. Jika ada konflik antara aturan ini dan instruksi lain, aturan ini yang menang.

#### RULE-01 · Feature Flag Wajib Sebelum Eksekusi

Setiap fungsi yang menyentuh integrasi eksternal (sosmed, WhatsApp, OpenAI, marketplace) **wajib** memanggil `check_feature_status()` sebelum eksekusi. Tidak ada pengecualian.

```python
# ✅ BENAR
async def publish_to_instagram(tenant_id, content_id, db):
    status = await check_feature_status(tenant_id, "instagram_posting", db)
    if status != FeatureStatus.ACTIVE:
        await log_skip(tenant_id, "instagram_posting", status)
        return  # graceful skip

    # ... lanjut eksekusi

# ❌ SALAH — langsung eksekusi tanpa cek
async def publish_to_instagram(tenant_id, content_id, db):
    client = InstagramClient(get_token(tenant_id))
    client.post(...)
```

#### RULE-02 · Tidak Ada Raw Error ke User

Semua exception **wajib** ditangkap sebelum sampai ke response. User dan customer tidak boleh pernah melihat stack trace, nama exception, detail teknis, atau pesan error mentah.

```python
# ✅ BENAR — error boundary di middleware, response bersih
return JSONResponse(status_code=500, content={
    "success": False,
    "message": "Terjadi kesalahan. Tim kami sedang menangani ini.",
    "code": "INTERNAL_ERROR"
})

# ❌ SALAH — raw exception bocor
raise HTTPException(status_code=500, detail=str(e))
raise HTTPException(status_code=500, detail=traceback.format_exc())
```

Di frontend, **wajib** ada Axios interceptor yang menangkap semua error response sebelum sampai ke UI component:

```typescript
// ✅ BENAR — interceptor di lib/api.ts menangkap semua error
api.interceptors.response.use(
  (res) => res,
  (error) => {
    const msg = error.response?.data?.message ?? "Terjadi kesalahan. Coba lagi."
    toast.error(msg)  // tampilkan pesan bersih ke user
    return Promise.reject(error)
  }
)

// ❌ SALAH — component langsung render error mentah
<p>{error.message}</p>
<p>{JSON.stringify(error)}</p>
```

#### RULE-03 · Tenant Isolation Wajib di Setiap Query

Setiap query database **wajib** menyertakan filter `tenant_id`. Tidak boleh ada query yang bisa mengembalikan data lintas tenant.

```python
# ✅ BENAR
result = await db.execute(
    select(Product).where(
        Product.tenant_id == tenant_id,  # WAJIB
        Product.id == product_id
    )
)

# ❌ SALAH — bisa ambil data tenant lain
result = await db.execute(
    select(Product).where(Product.id == product_id)
)
```

Tambahkan RLS policy di PostgreSQL sebagai lapisan kedua keamanan (defense in depth), bukan pengganti filter di kode.

#### RULE-04 · Setiap Celery Task Wajib Retry & Log

Semua Celery task wajib punya konfigurasi retry dan mencatat hasil ke `system_logs`. Tidak boleh ada task yang silent fail.

```python
# ✅ BENAR
@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,  # detik, akan di-backoff otomatis
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def run_content_publish(self, tenant_id: str, content_id: str):
    try:
        # ... eksekusi
        log_task_result(tenant_id, "content_publish", "success")
    except Exception as exc:
        log_task_result(tenant_id, "content_publish", "failed", str(exc))
        raise self.retry(exc=exc)

# ❌ SALAH — tidak ada retry, tidak ada log
@celery_app.task
def run_content_publish(tenant_id, content_id):
    publish_to_instagram(tenant_id, content_id)
```

#### RULE-05 · Secret & Credential Tidak Boleh di Kode

Tidak boleh ada API key, token, password, atau secret yang ditulis langsung di kode atau di-commit ke repo.

```python
# ✅ BENAR — selalu dari environment variable
import os
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# ❌ SALAH
OPENAI_API_KEY = "sk-proj-abc123..."
```

Semua credential tenant (token OAuth sosmed) disimpan ter-enkripsi di database menggunakan `encrypt_credential()` / `decrypt_credential()` dari `core/security.py`. Tidak boleh disimpan plaintext.

#### RULE-06 · Semua Input Wajib Divalidasi dengan Pydantic

Setiap request body dan response **wajib** menggunakan Pydantic v2 schema. Tidak boleh ada `dict` mentah yang masuk ke service layer atau database.

```python
# ✅ BENAR
class CreateProductRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    affiliate_link: HttpUrl
    base_price: Decimal = Field(..., gt=0)

@router.post("/products")
async def create_product(body: CreateProductRequest, ...):
    ...

# ❌ SALAH
@router.post("/products")
async def create_product(body: dict, ...):
    name = body.get("name")  # tidak tervalidasi
```

#### RULE-07 · FeatureGate Wajib di Setiap Fitur UI

Setiap halaman atau komponen yang bergantung pada integrasi eksternal **wajib** dibungkus `<FeatureGate>`. Tidak boleh ada tombol atau aksi yang bisa diklik tapi akan error karena integrasi belum dikonfigurasi.

```tsx
// ✅ BENAR
<FeatureGate feature="instagram_posting">
  <PostScheduler />
</FeatureGate>

// ❌ SALAH — tombol muncul tapi akan error saat diklik
<PostScheduler />
```

#### RULE-08 · Tidak Ada `print()` di Production Code

Gunakan `logging` Python yang terstruktur. Semua log harus punya context `tenant_id` jika relevan.

```python
# ✅ BENAR
import logging
logger = logging.getLogger(__name__)
logger.info("Content published", extra={"tenant_id": tenant_id, "post_id": post_id})

# ❌ SALAH
print(f"Content published for {tenant_id}")
```

#### RULE-09 · Database Migration Wajib via Alembic

Tidak boleh ada perubahan schema database yang dilakukan manual atau via `Base.metadata.create_all()` di production. Semua perubahan schema **wajib** melalui Alembic migration file.

```bash
# ✅ BENAR — buat migration dulu
alembic revision --autogenerate -m "add_tenant_id_to_leads"
alembic upgrade head

# ❌ SALAH — langsung create table
Base.metadata.create_all(bind=engine)
```

#### RULE-10 · Setiap Fungsi Publik Wajib Ada Type Hint

```python
# ✅ BENAR
async def check_feature_status(
    tenant_id: str,
    feature: str,
    db: AsyncSession
) -> FeatureStatus:
    ...

# ❌ SALAH
async def check_feature_status(tenant_id, feature, db):
    ...
```

---

### 0.4 Konvensi Penamaan

| Konteks | Konvensi | Contoh |
|---|---|---|
| Python file | `snake_case` | `engagement_worker.py` |
| Python class | `PascalCase` | `FeatureStatus`, `TenantCredential` |
| Python function/var | `snake_case` | `check_feature_status()`, `tenant_id` |
| React component | `PascalCase` | `FeatureGate.tsx`, `ContentQueue.tsx` |
| React hook | `camelCase` dengan prefix `use` | `useFeatureStatus`, `useTenant` |
| CSS class (Tailwind) | utility classes langsung | `className="flex gap-4 rounded-md"` |
| API endpoint | `kebab-case`, plural noun | `/api/v1/trending-products` |
| Celery task | `snake_case`, verb pertama | `run_instagram_posting`, `scan_trends` |
| DB tabel | `snake_case`, plural | `trending_products`, `tenant_credentials` |
| DB kolom | `snake_case` | `tenant_id`, `created_at` |
| Env variable | `UPPER_SNAKE_CASE` | `OPENAI_API_KEY`, `DATABASE_URL` |

---

### 0.5 Struktur Response API

Semua endpoint FastAPI **wajib** mengembalikan format konsisten berikut:

```python
# Success
{
    "success": True,
    "data": { ... },      # payload hasil
    "message": None       # opsional, string pesan
}

# Error (ditangani error_handler.py — tidak perlu dibuat manual di router)
{
    "success": False,
    "data": None,
    "message": "Pesan error ramah untuk user",
    "code": "ERROR_CODE_INTERNAL"   # kode untuk debugging, bukan stack trace
}
```

Gunakan base schema ini:

```python
# app/schemas/base.py
from typing import Generic, TypeVar, Optional
from pydantic import BaseModel

T = TypeVar("T")

class APIResponse(BaseModel, Generic[T]):
    success: bool
    data: Optional[T] = None
    message: Optional[str] = None

class APIError(BaseModel):
    success: bool = False
    data: None = None
    message: str
    code: str
```

---

### 0.6 Environment Variables yang Dibutuhkan

Buat file `.env.example` di root project dengan semua variabel berikut. Tidak boleh ada kode yang jalan tanpa variabel ini terdefinisi (gunakan `pydantic-settings` untuk validasi saat startup):

```bash
# App
APP_ENV=development
APP_SECRET_KEY=

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/reseller_ai

# Redis
REDIS_URL=redis://localhost:6379/0

# AI Provider (OpenRouter untuk dev, OpenAI untuk production)
# OpenRouter: https://openrouter.ai — daftar gratis, free models tersedia
OPENROUTER_API_KEY=
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
# Model default untuk dev (free tier OpenRouter):
AI_MODEL_FAST=meta-llama/llama-3.1-8b-instruct:free
AI_MODEL_QUALITY=meta-llama/llama-3.1-8b-instruct:free

# OpenAI (untuk production — opsional jika pakai OpenRouter)
OPENAI_API_KEY=

# Meta (Facebook / Instagram)
META_APP_ID=
META_APP_SECRET=

# TikTok
TIKTOK_CLIENT_KEY=
TIKTOK_CLIENT_SECRET=

# WhatsApp Business
WHATSAPP_TOKEN=
WHATSAPP_PHONE_NUMBER_ID=

# Midtrans
MIDTRANS_SERVER_KEY=
MIDTRANS_CLIENT_KEY=

# Stripe (opsional, untuk international)
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=

# Email
RESEND_API_KEY=

# Encryption (untuk enkripsi credential tenant)
CREDENTIAL_ENCRYPTION_KEY=

# Frontend
VITE_API_BASE_URL=http://localhost:8000
```

---

### 0.7 Checklist Sebelum Commit

Sebelum setiap commit, pastikan:

```
[ ] Semua fungsi yang menyentuh integrasi eksternal punya RULE-01 (feature flag check)
[ ] Tidak ada raw error yang bisa bocor ke response (RULE-02)
[ ] Semua query DB menyertakan filter tenant_id (RULE-03)
[ ] Semua Celery task punya retry & log (RULE-04)
[ ] Tidak ada secret/credential di kode (RULE-05)
[ ] Semua input menggunakan Pydantic schema (RULE-06)
[ ] Semua fitur UI baru dibungkus <FeatureGate> (RULE-07)
[ ] Tidak ada print() di kode (RULE-08)
[ ] Perubahan schema DB pakai Alembic migration (RULE-09)
[ ] Semua fungsi publik punya type hint (RULE-10)
[ ] .env.example diupdate jika ada env baru
[ ] Test ditulis untuk setiap service/function baru
```

---

## 1. Ringkasan Eksekutif

Sistem ini adalah **AI-Powered SaaS Platform** yang memungkinkan siapa pun menjadi reseller lebih efisien bertenaga AI. Setiap pengguna (tenant) mendapatkan workspace mandiri berisi dua mesin AI inti:

1. **Engagement Engine** — AI membalas komentar dan chat (DM/Messenger) secara real-time menggunakan konteks produk tenant, dengan human takeover mechanic.
2. **Lead Intelligence Engine** — AI mengklasifikasikan setiap percakapan masuk menjadi **hot / warm / cold lead**, sehingga reseller tahu persis siapa yang perlu di-follow up.

Platform ini dijual sebagai **Software as a Service (SaaS)** dengan model subscription. Satu sistem melayani banyak pengguna (multi-tenant), masing-masing terisolasi secara data, branding, dan konfigurasi AI-nya.

---

## 2. Tujuan & Lingkup

### 2.1 Tujuan
- Membangun platform SaaS yang dapat diakses ribuan tenant secara bersamaan.
- Otomatisasi end-to-end: discovery → marketing → engagement → konversi per tenant.
- Menyediakan dashboard mandiri bagi tiap tenant untuk monitoring, approval, dan kontrol AI.
- Menghasilkan recurring revenue dari model subscription.

### 2.2 Lingkup (In Scope)
- Sistem multi-tenant dengan isolasi data per workspace.
- Auto-reply chat (Facebook Messenger DM) dan komentar Facebook Page.
- Lead classification otomatis: hot / warm / cold dari setiap percakapan masuk.
- Dashboard Inbox: monitoring percakapan + human takeover per chat.
- Dashboard Leads: daftar lead terklasifikasi + filter status.
- Onboarding tenant: registrasi, koneksi Facebook Page, setup produk.
- Manajemen subscription & billing (plan Free / Starter / Pro / Enterprise).
- Super Admin dashboard untuk memantau seluruh tenant, usage, dan kesehatan sistem.

### 2.3 Di Luar Lingkup (Out of Scope)
- Generasi konten / caption otomatis.
- Penjadwalan & publikasi konten ke sosmed.
- Product discovery / trend scanning.
- Auto-send link checkout / affiliate.
- Manajemen stok & logistik fisik.
- Pembayaran langsung di dalam chat.
- Mobile native app (prioritas web dashboard dulu).

---

## 3. Arsitektur Sistem

### 3.1 Gambaran Umum Arsitektur SaaS Multi-Tenant

```
┌──────────────────────────────────────────────────────────────────────────┐
│                          PUBLIC LAYER                                     │
│   Landing Page · Pricing · Docs  (React + Vite / Static)                 │
└─────────────────────────────┬────────────────────────────────────────────┘
                              │
┌─────────────────────────────▼────────────────────────────────────────────┐
│                        AUTH & TENANT LAYER                                │
│   Registration · Login · OAuth · Workspace Init · Plan Selection          │
│   (FastAPI Auth + JWT + OAuth2 — Tenant Provisioning Service)             │
└──────┬──────────────────────┬───────────────────────┬────────────────────┘
       │                      │                        │
  [Tenant A]             [Tenant B]               [Tenant C ...]
       │                      │                        │
┌──────▼──────────────────────▼────────────────────────▼────────────────────┐
│                       DASHBOARD LAYER (per tenant)                         │
│   Inbox · Leads · Products · Settings · Billing                            │
│   (React SPA, data selalu di-scope ke tenant_id)                           │
└──────────────────────────────────┬─────────────────────────────────────────┘
                                   │
┌──────────────────────────────────▼─────────────────────────────────────────┐
│                          API GATEWAY                                         │
│   Rate limiting · Auth middleware · Tenant context injection · Logging       │
│   (FastAPI Middleware)                                                       │
└──────────────────────┬───────────────────────────────────────────────────────┘
                       │
        ┌──────────────┴──────────────┐
        │                             │
┌───────▼───────┐             ┌───────▼───────┐
│  ENGAGEMENT   │             │     LEAD      │
│    ENGINE     │             │ INTELLIGENCE  │
│               │             │    ENGINE     │
└───────┬───────┘             └───────┬───────┘
        │                             │
┌───────▼─────────────────────────────▼───────┐
│              ORCHESTRATOR LAYER              │
│    (Celery + Redis — task queue per tenant)  │
└─────────────────────┬───────────────────────┘
                      │
┌─────────────────────▼───────────────────────┐
│                AI / LLM LAYER               │
│   OpenRouter / OpenAI — chat, intent,       │
│   lead classification                       │
│   text-embedding-3-small · pgvector (RAG)   │
└─────────────────────┬───────────────────────┘
                      │
┌─────────────────────▼───────────────────────┐
│                 DATA LAYER                  │
│   PostgreSQL 16 (Row-Level Security)        │
│   pgvector (knowledge base per tenant)      │
│   Redis 7 — Celery broker & event queue     │
└─────────────────────────────────────────────┘

External Integrations (per tenant, credential disimpan ter-enkripsi):
  - Meta Graph API (FB Page komentar + Messenger DM)
  - Billing: Midtrans (Indonesia) / Stripe (international)
  - Email notifikasi: Resend / Sendgrid
```

### 3.2 Komponen Utama

| Komponen | Fungsi | Teknologi |
|---|---|---|
| Auth & Tenant Service | Registrasi, login, provisioning workspace baru | FastAPI + JWT + OAuth2 + PostgreSQL |
| API Gateway | Rate limiting, inject tenant context, log request | FastAPI Middleware & Dependency Injection |
| Orchestrator | Workflow event-driven per tenant | Celery + Redis |
| LLM Core | Intent detection, chat RAG, lead classification | OpenRouter / OpenAI — GPT-4o-mini |
| Vector DB | Knowledge base produk per tenant (RAG) | pgvector (PostgreSQL extension) + text-embedding-3-small |
| Relational DB | Semua data bisnis, multi-tenant RLS | PostgreSQL |
| Message Queue | Antrian event comment/DM per tenant | Redis 7 (Celery broker) |
| FB Connector | Webhook receive + reply (Page komentar + Messenger) | Meta Graph API |
| Billing Service | Subscription, invoice, usage metering | Midtrans / Stripe |
| Dashboard (Tenant) | Inbox + Leads + Settings per tenant | React + Vite + Tailwind CSS |
| Super Admin Panel | Monitor semua tenant, usage, support | React + Vite (protected route) |

---

## 4. Multi-Tenancy Design

### 4.1 Strategi Isolasi Data

Sistem menggunakan **shared database + Row-Level Security (RLS)** di PostgreSQL dengan **two-layer defense**:

**Layer 1 (primary) — Application-level filter:**
Setiap query wajib menyertakan filter `tenant_id` eksplisit (RULE-03). Ini adalah garis pertahanan utama.

**Layer 2 (defense-in-depth) — RLS via `SET LOCAL`:**
Setiap database session meng-inject `tenant_id` via `SET LOCAL` di dalam transaction, sehingga RLS policy menjadi jaring pengaman jika layer 1 terlewat.

```python
# app/core/database.py — dependency per request
async def get_db_session(request: Request) -> AsyncSession:
    tenant_id = request.state.tenant_id
    async with AsyncSession(engine) as session:
        async with session.begin():
            # SET LOCAL: scoped ke transaction ini saja — aman dengan connection pooling
            await session.execute(
                text("SET LOCAL app.current_tenant_id = :tid"),
                {"tid": str(tenant_id)}
            )
            yield session
```

```sql
-- RLS policy (defense-in-depth, bukan pengganti filter aplikasi)
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON conversations
  USING (tenant_id = current_setting('app.current_tenant_id')::uuid);
```

> **Catatan pooling:** `SET LOCAL` aman dengan PgBouncer transaction mode karena scope-nya mati di akhir transaction — tidak ada state yang bocor ke koneksi lain.

Untuk data sensitif (token OAuth, WA credentials), disimpan terenkripsi di tabel `tenant_credentials` menggunakan AES-256 dengan key per tenant.

### 4.2 Credential Sosmed Per Tenant — Shared App Model

Platform menggunakan **satu Facebook App milik developer** (Shared App Model) yang sudah melewati Meta App Review. Setiap tenant menghubungkan **Facebook Page milik mereka sendiri** melalui OAuth — bukan membuat Meta App sendiri.

Keuntungan model ini:
- Tenant tidak perlu mendaftarkan Meta App sendiri atau melewati App Review
- Developer mengontrol satu App ID untuk semua tenant
- Setiap tenant tetap terisolasi — masing-masing punya `page_access_token` sendiri yang disimpan terenkripsi di `tenant_credentials`

Token disimpan ter-enkripsi (AES-256) dan digunakan eksklusif untuk tenant tersebut. Sistem tidak pernah mencampur token antar tenant.

### 4.3 AI Context Per Tenant

Setiap tenant memiliki:
- **Vector namespace** tersendiri di pgvector — diimplementasikan via filter `tenant_id` di tabel `product_embeddings` (lihat Section 7). pgvector tidak punya namespace native; isolasi dijamin oleh RULE-03 + RLS.
- **System prompt** yang bisa dikustomisasi (nama toko, tone bahasa, kebijakan toko).
- **Konfigurasi AI** tersendiri: threshold intent, auto-approve toggle, jam posting, dll.

### 4.4 Alur OAuth — Tenant Menghubungkan Facebook Page

Alur ini akan diimplementasikan di Fase 3 (Settings → Connect sosmed). Berikut desain targetnya:

```
1. Tenant klik "Hubungkan Facebook Page" di halaman Settings
        ↓
2. Backend generate OAuth URL:
   https://www.facebook.com/v19.0/dialog/oauth
     ?client_id={META_APP_ID}
     &redirect_uri={META_REDIRECT_URI}
     &scope=pages_manage_posts,pages_read_engagement,pages_messaging
     &state={tenant_id}   ← anti-CSRF, verifikasi saat callback
        ↓
3. Tenant login ke Facebook & grant izin
        ↓
4. Meta redirect ke: GET /auth/facebook/callback?code=...&state={tenant_id}
        ↓
5. Backend tukar `code` → short-lived user token
   (POST ke https://graph.facebook.com/v19.0/oauth/access_token)
        ↓
6. Backend tukar user token → long-lived page access token per Page:
   GET /me/accounts?access_token={user_token}
   → array Facebook Pages yang dikelola tenant
   → ambil page_access_token per Page (long-lived by default)
        ↓
7. Simpan terenkripsi di tenant_credentials:
   {
     tenant_id,
     platform: "facebook",
     access_token_encrypted: encrypt(page_access_token),
     metadata: { page_id, page_name }  ← simpan di kolom JSONB
   }
        ↓
8. FeatureStatus "facebook_reply" → ACTIVE
   (check_feature_status() menemukan credential valid)
```

**Env vars yang dibutuhkan (tambah ke .env.example):**
```bash
META_REDIRECT_URI=https://reseller.jawakoentji.my.id/auth/facebook/callback
META_OAUTH_SCOPES=pages_manage_posts,pages_read_engagement,pages_messaging
```

**Catatan implementasi:**
- `state` parameter di OAuth URL harus divalidasi saat callback untuk mencegah CSRF
- Jika tenant punya lebih dari satu Page, tampilkan daftar Pages untuk dipilih
- Long-lived page token tidak expire secara otomatis kecuali user cabut izin atau password Facebook berubah
- Simpan `expires_at = None` untuk long-lived page token (tidak ada expiry)

---

## 5. Desain Modul (AI Engines)

### 5.1 Modul 1 — Engagement Engine

**Tujuan:** Auto-reply komentar dan chat menggunakan konteks produk & brand tenant.

**Platform scope (Fase 2):** Facebook Page (komentar + Messenger DM). Platform lain (IG, WhatsApp, TikTok) ditambahkan di fase berikutnya.

**AI Provider:** OpenRouter API (OpenAI-compatible) — abstraksi di `openai_service.py` via env vars sehingga swap ke provider lain tidak butuh perubahan kode.

**Alur Proses:**
1. Webhook Facebook masuk ke `POST /webhooks/facebook` → diverifikasi signature → event dipush ke Redis queue.
2. `engagement_worker` ambil event dari queue → cek `check_feature_status()` (RULE-01).
3. Cek `is_human_takeover` di tabel `conversations` — jika `True`, skip seluruh proses AI untuk conversation itu.
4. Event di-enrich: histori chat customer, produk aktif tenant, FAQ dari vector DB tenant (pgvector RAG).
5. LLM (via OpenRouter) klasifikasi intent: `tanya_info` | `niat_beli` | `komplain` | `spam`.
6. Jika intent `komplain` atau pesan mengandung topik blacklist tenant → eskalasi: set `is_human_takeover = True`, catat di `system_logs`, skip auto-reply.
7. Jika lolos guardrail → LLM generate balasan dengan RAG context + tone tenant.
8. Balasan dikirim via Meta Graph API dan dicatat ke `conversations`.

**Human Takeover Mechanic:**
- Kolom `is_human_takeover: bool` di tabel `conversations` (default `False`)
- Toggle via `PATCH /api/v1/conversations/{id}/takeover`
- Saat `True`: AI skip conversation itu sampai tenant mengaktifkan kembali
- Eskalasi otomatis set `is_human_takeover = True`
- Inbox frontend polling setiap 10 detik (WebSocket ditambah di Fase 4)

**Guardrail:**
- Rate limiting per akun sosmed.
- Topik blacklist dikonfigurasi per tenant via `ai_config.escalation_topics` (array string).
- AI tidak boleh membuat klaim di luar data produk resmi tenant (RAG-only, tidak hallucinate).

### 5.3 Modul 3 — Lead Intelligence Engine

**Tujuan:** Mengklasifikasikan setiap percakapan masuk menjadi lead hot / warm / cold sehingga reseller tahu siapa yang perlu di-follow up manual.

**Alur Proses:**
1. Setiap conversation diproses oleh Engagement Engine (Modul 1) → intent + sentiment sudah tersedia di `conversations`.
2. `lead_worker` membaca conversation yang baru diupdate → jalankan `classify_lead()`.
3. LLM menentukan lead tier berdasarkan:
   - Intent: `niat_beli` → cenderung hot
   - Sentiment: positif / netral / negatif
   - Histori interaksi: berapa kali tanya, sudah berapa lama
   - Respons terhadap reply AI
4. Hasil klasifikasi disimpan ke tabel `leads` dengan `tier: hot | warm | cold`.
5. Hot lead → muncul di bagian atas Leads dashboard + badge merah.

**Kriteria Tier:**

| Tier | Sinyal |
|------|--------|
| **Hot** | Intent `niat_beli` + sentiment positif + aktif dalam 24 jam |
| **Warm** | Intent `tanya_info` + bertanya lebih dari 1 kali, atau `niat_beli` tapi belum ada respons positif |
| **Cold** | Intent `spam` atau tidak ada aktivitas lanjutan setelah reply pertama |

**Output:** Tabel leads terklasifikasi → ditampilkan di Leads dashboard per tenant.

---

## 6. Subscription & Billing

### 6.1 Struktur Plan

| Plan | Harga/bulan | Akun Sosmed | AI Post/bulan | AI Reply/bulan | Fitur Ekstra |
|---|---|---|---|---|---|
| **Free** | Grp 0 | 1 | 10 | 50 | Dashboard basic |
| **Starter** | Rp 149.000 | 3 | 60 | 500 | Analytics dasar, 1 niche |
| **Pro** | Rp 399.000 | 10 | 300 | 3.000 | Multi-niche, custom AI tone, priority queue |
| **Enterprise** | Custom | Unlimited | Unlimited | Unlimited | White-label, dedicated support, SLA |

### 6.2 Usage Metering

Setiap API call AI (post generated, reply sent) dicatat di tabel `usage_logs` per tenant per bulan. Jika kuota hampir habis → notifikasi email + banner di dashboard. Jika habis → AI paused, tenant diarahkan upgrade plan.

### 6.3 Billing Flow

1. Tenant pilih plan → redirect ke Midtrans/Stripe hosted checkout page.
2. Konfirmasi pembayaran → webhook update status plan tenant.
3. Subscription renewal otomatis bulanan.
4. Invoice otomatis dikirim via email.

---

## 7. Skema Data (Multi-Tenant)

```sql
-- Auth & user management
users (
  id UUID PK,
  tenant_id UUID FK NULLABLE,  -- NULL jika role = 'super_admin'
  email VARCHAR(255) UNIQUE NOT NULL,
  password_hash VARCHAR(255),
  role VARCHAR(20) NOT NULL,   -- 'tenant_user' | 'super_admin'
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ
)
-- Rule: super_admin bypass semua tenant filter
-- Rule: tenant_user selalu scoped ke tenant_id miliknya (RULE-03)

-- Core tenant management
tenants (
  id UUID PK, name, email, plan, plan_expires_at,
  ai_config JSONB,  -- struktur lengkap:
  -- {
  --   "tone": "casual",              -- gaya bahasa AI
  --   "niche": [],                   -- kategori produk tenant
  --   "posting_hours": [9, 12, 19],  -- jam optimal posting
  --   "intent_threshold": 0.75,      -- confidence minimum niat_beli
  --   "auto_approve": false,         -- auto-post tanpa approval
  --   "escalation_topics": [         -- topik yang wajib dijawab manusia
  --     "penipuan", "refund", "harga salah", "komplain pengiriman"
  --   ]
  -- }
  created_at
)

tenant_credentials (
  id, tenant_id FK, platform,
  access_token_encrypted, refresh_token_encrypted,
  expires_at, updated_at
)

-- Usage & billing
subscriptions (
  id, tenant_id, plan, status, current_period_start,
  current_period_end, midtrans_subscription_id
)

usage_logs (
  id, tenant_id, resource_type(post/reply/discovery),
  count, period_month, updated_at
)

-- Business data (semua ber-tenant_id, dilindungi RLS)
products (
  id, tenant_id, name, category, supplier_link,
  base_price, margin_estimate, affiliate_link, status
)

conversations (
  id UUID PK,
  tenant_id UUID FK NOT NULL,
  customer_id UUID FK NOT NULL,
  platform VARCHAR(50),          -- 'facebook' | 'messenger' | 'instagram' | 'whatsapp'
  channel_type VARCHAR(50),      -- 'comment' | 'dm'
  platform_message_id VARCHAR(255),  -- ID pesan dari platform (untuk dedup)
  message_in TEXT,
  message_out TEXT,
  intent VARCHAR(50),            -- 'tanya_info' | 'niat_beli' | 'komplain' | 'spam'
  sentiment VARCHAR(20),         -- 'positive' | 'neutral' | 'negative'
  is_human_takeover BOOLEAN DEFAULT false,  -- True = AI skip, manusia handle
  escalation_reason VARCHAR(100),           -- alasan eskalasi jika is_human_takeover=True
  created_at TIMESTAMPTZ
)

leads (
  id UUID PK,
  tenant_id UUID FK NOT NULL,
  customer_id UUID FK NOT NULL,
  conversation_id UUID FK NOT NULL,   -- percakapan yang memicu lead ini
  tier VARCHAR(10) NOT NULL,           -- 'hot' | 'warm' | 'cold'
  tier_reason TEXT,                    -- penjelasan singkat dari LLM
  classified_at TIMESTAMPTZ,
  last_interaction_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ
)

customers (
  id UUID PK,
  tenant_id UUID FK NOT NULL,
  platform_user_id VARCHAR(255),    -- ID user dari platform
  platform VARCHAR(50),             -- 'facebook' | 'messenger' | dsb.
  name VARCHAR(255),
  handle VARCHAR(255),
  first_seen TIMESTAMPTZ,
  tags JSONB
)

-- Vector search (pgvector) — namespace per tenant via tenant_id filter
product_embeddings (
  id UUID PK,
  tenant_id UUID FK NOT NULL,
  product_id UUID FK NULLABLE,     -- NULL jika embedding dari FAQ/brand voice
  content_type VARCHAR(50),        -- 'product' | 'faq' | 'brand_voice'
  content_text TEXT NOT NULL,      -- teks asli yang di-embed
  embedding VECTOR(1536),          -- text-embedding-3-small output
  metadata JSONB,                  -- data tambahan (platform, tags, dsb.)
  created_at TIMESTAMPTZ
)
-- Index wajib:
-- CREATE INDEX ON product_embeddings USING ivfflat (embedding vector_cosine_ops);
-- CREATE INDEX ON product_embeddings (tenant_id);

-- System & ops
system_logs (
  id UUID PK,
  tenant_id UUID FK NULLABLE,  -- NULL jika error level sistem
  engine VARCHAR(50),          -- 'content_engine' | 'engagement_engine' | dsb.
  action VARCHAR(100),
  status VARCHAR(20),          -- 'success' | 'failed' | 'skipped'
  error_code VARCHAR(100),     -- kode internal, bukan raw exception
  error_message TEXT,          -- deskripsi singkat internal
  context JSONB,               -- data konteks saat event terjadi
  created_at TIMESTAMPTZ
)
```

---

## 8. Dashboard — Fitur Per Peran

### 8.1 Tenant Dashboard

| Halaman | Konten |
|---|---|
| **Overview** | Ringkasan: percakapan masuk, leads hari ini, hot leads aktif |
| **Products** | Kelola katalog produk + deskripsi (dipakai untuk RAG context AI reply) |
| **Inbox** | Semua percakapan aktif, bisa human-takeover per chat |
| **Leads** | Daftar lead terklasifikasi: hot / warm / cold + filter + detail percakapan |
| **Settings** | Connect Facebook Page, konfigurasi AI tone, topik eskalasi |
| **Billing** | Status plan, usage meter, upgrade, invoice |

### 8.2 Super Admin Dashboard

| Halaman | Konten |
|---|---|
| **Tenant List** | Semua tenant, plan, status, last active |
| **System Health** | Queue depth, API error rate, LLM latency, platform webhook status |
| **Usage Overview** | Total AI calls, paling banyak digunakan, mendekati limit |
| **Revenue** | MRR, churn, konversi free → paid |
| **Support** | Tiket masuk, log error per tenant |

---

## 9. Alur Onboarding Tenant

```
1. Daftar akun (email + password)
       ↓
2. Connect Facebook Page via OAuth
       ↓
3. Pilih subscription plan (atau mulai Free)
       ↓
4. Setup AI: nama toko, tone bahasa (formal/casual/gaul), topik eskalasi
       ↓
5. Tambah produk pertama (manual — dipakai sebagai konteks RAG untuk AI reply)
       ↓
6. Dashboard aktif — AI mulai balas komentar & DM, lead masuk otomatis
```

---

## 10. Alur End-to-End (Contoh Tenant "Toko Kece")

1. **T+19:15** — Customer komentar di Facebook Page: "lucu banget kak ada warna lain?". Webhook masuk → Celery task.
2. **T+19:15+30s** — AI classify intent: `tanya_info`, sentiment: positif. AI balas: "Ada 5 warna kak, mau yang mana? DM aku ya 😊".
3. **T+19:22** — Customer DM via Messenger: "mau yang hijau sage, berapa?". AI balas dengan info harga + detail produk dari RAG.
4. **T+19:22** — Intent re-classified: `niat_beli`, sentiment positif, aktif < 24 jam → Lead tier: **Hot**. Lead masuk Leads dashboard.
5. **T+19:25** — Tenant buka dashboard, lihat badge "Hot Lead — Sarah". Reseller follow up manual.

---

## 11. Kebutuhan Non-Fungsional

| Aspek | Target |
|---|---|
| Response time chat/komentar | < 2 menit |
| API Gateway latency | < 200ms (p95) |
| Uptime | 99.9% (SLA untuk plan Pro ke atas) |
| Skalabilitas tenant | Mendukung 10.000+ tenant aktif |
| Isolasi data | Zero data leakage antar tenant (RLS + enkripsi) |
| Keamanan credential | Token OAuth dienkripsi AES-256 per tenant |
| Audit trail | Semua aksi AI tercatat & bisa direview tenant |
| GDPR / privasi | Data customer bisa dihapus atas permintaan (right to erasure) |

---

## 12. Risiko & Mitigasi

| Risiko | Mitigasi |
|---|---|
| Data bocor antar tenant | RLS ketat di DB + integration test multi-tenant wajib |
| Platform blokir akun tenant karena bot | Rate limiting + variasi konten + edukasi tenant soal best practice |
| AI memberi info produk salah | RAG hanya dari data resmi + tenant bisa review sebelum reply otomatis aktif |
| Abuse Free plan (spam akun) | Email verification + CAPTCHA + limit ketat di Free tier |
| Kebijakan WA Business API auto-reply | Gunakan template message + opt-in customer |
| Satu tenant LLM usage sangat besar | Usage cap per plan + circuit breaker per tenant |
| Churn tinggi karena hasil AI kurang bagus | Onboarding guided, contoh output di demo, free trial 7 hari Pro |

---

## 13. Roadmap Implementasi

### Fase 1 — Fondasi ✅ SELESAI
> Auth, DB, Celery, tenant isolation, feature flags.

### Fase 2 — Engagement Engine ✅ SELESAI
> AI CS otomatis: webhook Facebook, intent classify, auto-reply, Inbox dashboard.

### Fase 3 — Lead Intelligence
> Klasifikasi lead hot/warm/cold dari percakapan masuk + Leads dashboard.

### Fase 4 — SaaS Layer
> Subscription & billing (Midtrans/Stripe), usage metering, quota enforcement, Super Admin panel.

### Fase 5 — Ekspansi (Opsional, post-launch)
> Berdasarkan feedback pengguna — misalnya: platform tambahan (IG DM, WhatsApp), analytics lebih dalam, atau fitur lain yang terbukti dibutuhkan pasar.

---

## 14. Tech Stack Lengkap

### 14.1 Stack Utama

| Layer | Teknologi | Keterangan |
|---|---|---|
| **Frontend** | React 18 + Vite + Tailwind CSS + shadcn/ui | SPA per tenant, routing via React Router v6 |
| **Backend API** | FastAPI (Python 3.12) | Async, OpenAPI docs otomatis, Dependency Injection untuk tenant context |
| **Auth** | FastAPI + JWT (python-jose) + OAuth2 | Login email/pass & Google OAuth, refresh token rotation |
| **Task Queue & Scheduler** | Celery 5 + Celery Beat + Redis 7 | Worker per engine, task terjadwal, retry logic built-in |
| **Message Broker / Cache** | Redis 7 | Celery broker, session cache, rate limit counter |
| **Database** | PostgreSQL 16 + pgvector | Row-Level Security per tenant, vector search untuk RAG |
| **ORM** | SQLAlchemy 2.0 + Alembic | Async ORM, migrasi terkelola |
| **AI / LLM** | OpenRouter API (OpenAI-compatible) + OpenAI API | Dev/testing: OpenRouter free tier. Production: OpenAI GPT-4o + GPT-4o-mini. Abstraksi via `openai_service.py` — swap cukup ubah env vars |
| **AI Embedding** | OpenAI text-embedding-3-small | Embed katalog produk + FAQ ke pgvector |
| **Image Generation** | OpenAI DALL·E 3 | Buat visual promosi produk otomatis |
| **Object Storage** | Cloudflare R2 / AWS S3 | Media aset per tenant |
| **CDN** | Cloudflare | Serve media cepat ke seluruh Indonesia |
| **Billing** | Midtrans (Indonesia) + Stripe (international) | Webhook konfirmasi payment, subscription management |
| **Email** | Resend / Sendgrid | Notifikasi onboarding, invoice, alert |
| **Monitoring** | Grafana + Prometheus + Sentry | Metrics sistem, error tracking per tenant |
| **Infra (MVP)** | Railway / Render | Deploy cepat, managed PostgreSQL + Redis |
| **Infra (Scale)** | AWS ECS / GCP Cloud Run + RDS | Auto-scaling container, managed DB |
| **CI/CD** | GitHub Actions | Test, lint, deploy otomatis |

### 14.2 Struktur Project

```
reseller-ai/
│
├── backend/                        # FastAPI
│   ├── app/
│   │   ├── main.py                 # Entry point, middleware, router registry
│   │   ├── core/
│   │   │   ├── config.py           # Settings (env vars, feature flags)
│   │   │   ├── database.py         # SQLAlchemy async engine + PostgreSQL
│   │   │   ├── redis.py            # Redis client
│   │   │   ├── security.py         # JWT, password hashing
│   │   │   └── feature_flags.py    # checkFeatureStatus() — graceful degradation
│   │   ├── middleware/
│   │   │   ├── tenant_context.py   # Inject tenant_id ke setiap request
│   │   │   ├── error_handler.py    # Global error boundary, no raw error ke user
│   │   │   └── rate_limiter.py     # Per-tenant rate limiting via Redis
│   │   ├── models/                 # SQLAlchemy models (tenants, products, dll)
│   │   ├── schemas/                # Pydantic v2 schemas (request/response)
│   │   ├── routers/
│   │   │   ├── auth.py
│   │   │   ├── tenants.py
│   │   │   ├── products.py
│   │   │   ├── content.py
│   │   │   ├── conversations.py
│   │   │   ├── leads.py
│   │   │   └── billing.py
│   │   ├── services/
│   │   │   ├── openai_service.py   # OpenAI wrapper (GPT-4o, DALL·E 3, embedding)
│   │   │   ├── rag_service.py      # pgvector search + prompt assembly
│   │   │   ├── social_service.py   # Meta / TikTok API connector
│   │   │   └── billing_service.py  # Midtrans / Stripe
│   │   └── workers/                # Celery tasks
│   │       ├── celery_app.py
│   │       ├── discovery_worker.py
│   │       ├── content_worker.py
│   │       ├── engagement_worker.py
│   │       └── conversion_worker.py
│   ├── alembic/                    # DB migrations
│   └── tests/
│
└── frontend/                       # React + Vite
    ├── src/
    │   ├── main.tsx
    │   ├── App.tsx
    │   ├── pages/
    │   │   ├── Dashboard.tsx
    │   │   ├── Products.tsx
    │   │   ├── ContentQueue.tsx
    │   │   ├── Inbox.tsx
    │   │   ├── Leads.tsx
    │   │   ├── Analytics.tsx
    │   │   ├── Settings.tsx        # Connect sosmed, API keys, AI config
    │   │   └── Billing.tsx
    │   ├── components/
    │   │   ├── FeatureGate.tsx     # Disable/show notice jika fitur belum aktif
    │   │   ├── SetupChecklist.tsx
    │   │   └── ui/                 # shadcn/ui components
    │   ├── hooks/
    │   │   ├── useFeatureStatus.ts # Fetch status tiap integrasi dari API
    │   │   └── useTenant.ts
    │   └── lib/
    │       └── api.ts              # Axios client + interceptor error handling
    └── public/
```

### 14.3 Pemetaan Model Per Engine

| Engine | Model Dev (OpenRouter free) | Model Production (OpenAI) | Alasan |
|---|---|---|---|
| RAG embedding (produk/FAQ) | — (skip dev, gunakan dummy vector) | `text-embedding-3-small` | Cepat, akurasi cukup |
| Engagement chat reply | `llama-3.1-8b-instruct:free` | `gpt-4o-mini` | Volume tinggi, latency rendah |
| Intent classification | `llama-3.1-8b-instruct:free` + structured output | `gpt-4o-mini` + structured output | Deteksi intent |
| Lead classification (hot/warm/cold) | `llama-3.1-8b-instruct:free` + structured output | `gpt-4o-mini` + structured output | Volume sedang, output terstruktur |

> **Abstraksi provider:** `openai_service.py` menggunakan `openai` Python SDK dengan `base_url` dan `api_key` dari env vars. Swap provider = ubah 2 env vars, zero code change.

```python
# Dev (OpenRouter)
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_API_KEY=sk-or-...
AI_MODEL_FAST=meta-llama/llama-3.1-8b-instruct:free

# Production (OpenAI)
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_API_KEY=sk-proj-...
AI_MODEL_FAST=gpt-4o-mini
```

### 14.4 Implementasi Feature Flag (FastAPI — Python)

```python
# app/core/feature_flags.py

from enum import Enum
from sqlalchemy.ext.asyncio import AsyncSession

class FeatureStatus(str, Enum):
    ACTIVE = "active"
    NOT_CONFIGURED = "not_configured"
    EXPIRED = "expired"
    PLAN_LOCKED = "plan_locked"
    QUOTA_EXCEEDED = "quota_exceeded"
    DISABLED_BY_USER = "disabled_by_user"

PLAN_FEATURES = {
    "free":       ["instagram_reply"],
    "starter":    ["instagram_reply", "tiktok_reply", "content_publish"],
    "pro":        ["instagram_reply", "tiktok_reply", "facebook_reply",
                   "whatsapp_reply", "content_publish",
                   "product_discovery", "sales_conversion", "analytics"],
    "enterprise": ["*"],
}

async def check_feature_status(
    tenant_id: str,
    feature: str,
    db: AsyncSession
) -> FeatureStatus:
    try:
        tenant = await get_tenant(tenant_id, db)
        plan_features = PLAN_FEATURES.get(tenant.plan, [])

        if "*" not in plan_features and feature not in plan_features:
            return FeatureStatus.PLAN_LOCKED

        if await is_quota_exceeded(tenant_id, feature, db):
            return FeatureStatus.QUOTA_EXCEEDED

        credential = await get_credential(tenant_id, feature, db)
        if not credential:
            return FeatureStatus.NOT_CONFIGURED
        if credential.is_expired():
            return FeatureStatus.EXPIRED

        return FeatureStatus.ACTIVE

    except Exception:
        return FeatureStatus.NOT_CONFIGURED  # safe default


# Digunakan di Celery worker:
async def run_instagram_posting(tenant_id: str, content_id: str, db):
    status = await check_feature_status(tenant_id, "instagram_posting", db)
    if status != FeatureStatus.ACTIVE:
        await log_skip(tenant_id, "instagram_posting", status)
        return  # graceful skip — tidak raise, tidak crash
    # lanjut eksekusi normal...
```

### 14.5 Global Error Boundary (FastAPI)

```python
# app/middleware/error_handler.py

from fastapi import Request
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger("internal")

async def global_exception_handler(request: Request, exc: Exception):
    # Stack trace hanya ke log internal — TIDAK ke response
    logger.error(
        "Unhandled exception",
        extra={
            "path": str(request.url),
            "tenant_id": getattr(request.state, "tenant_id", None),
            "error_type": type(exc).__name__,
        },
        exc_info=True
    )

    # Response ke user: pesan generik, zero raw error
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "Terjadi kesalahan sistem. Tim kami sedang menangani ini.",
            "code": "INTERNAL_ERROR"
            # TIDAK ada: detail exc, stack trace, nama file, line number
        }
    )

# Didaftarkan di main.py:
# app.add_exception_handler(Exception, global_exception_handler)
```

### 14.6 FeatureGate Component (React)

```tsx
// components/FeatureGate.tsx

import { useFeatureStatus } from '@/hooks/useFeatureStatus'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'

const STATUS_CONFIG: Record<string, {
  title: string; desc: string; action?: string; href?: string
}> = {
  not_configured: {
    title: "Belum terhubung",
    desc: "Hubungkan integrasi ini untuk mengaktifkan fitur.",
    action: "Buka Settings", href: "/settings/integrations",
  },
  expired: {
    title: "Koneksi kedaluwarsa",
    desc: "Sambungkan ulang akun kamu untuk melanjutkan.",
    action: "Reconnect", href: "/settings/integrations",
  },
  plan_locked: {
    title: "Tersedia di plan lebih tinggi",
    desc: "Upgrade untuk mengakses fitur ini.",
    action: "Lihat Plan", href: "/billing",
  },
  quota_exceeded: {
    title: "Kuota bulan ini sudah habis",
    desc: "Upgrade atau tunggu reset bulan depan.",
    action: "Upgrade Plan", href: "/billing",
  },
}

export function FeatureGate({
  feature,
  children,
}: {
  feature: string
  children: React.ReactNode
}) {
  const { status, isLoading } = useFeatureStatus(feature)

  if (isLoading)
    return <div className="animate-pulse h-10 bg-muted rounded-md" />

  if (status === 'active') return <>{children}</>

  const cfg = STATUS_CONFIG[status]
  if (!cfg) return null

  return (
    <Alert className="flex items-start justify-between gap-4">
      <div>
        <AlertTitle>{cfg.title}</AlertTitle>
        <AlertDescription>{cfg.desc}</AlertDescription>
      </div>
      {cfg.action && (
        <Button size="sm" variant="outline" asChild>
          <a href={cfg.href}>{cfg.action}</a>
        </Button>
      )}
    </Alert>
  )
}

// Cara pakai:
// <FeatureGate feature="instagram_posting">
//   <PostScheduler />
// </FeatureGate>
```

### 14.7 UI Design System — Impeccable

Frontend project ini menggunakan **[Impeccable](https://impeccable.style/)** sebagai design skill system untuk AI coding agent (Claude Code, Cursor, Copilot, dsb.).

Impeccable memberikan kosakata desain bersama antara developer dan AI agent — sehingga output frontend tidak terlihat generik atau "AI-generated". Impeccable dijalankan di atas stack yang sudah ada (React + Vite + Tailwind CSS + shadcn/ui) dan menghormati token serta komponen yang sudah terdefinisi, bukan menggantikannya.

#### Setup

```bash
# Install Impeccable (butuh Node 24+)
npx impeccable install

# Inisialisasi — jalankan sekali di awal project
/impeccable init
```

Setelah init, Impeccable akan membuat dua file di root frontend:

- **`DESIGN.md`** — dokumentasi visual system (palette, tipografi, komponen, aturan brand) dalam format Google Stitch. Wajib di-commit ke repo dan dijaga tetap sinkron dengan perubahan desain.
- **`PRODUCT.md`** — konteks produk untuk agent: siapa user-nya, register produk, brand voice, dan anti-references. Digunakan setiap command Impeccable sebelum menghasilkan UI.

#### Isi PRODUCT.md (isi sesuai proyek ini)

```markdown
# PRODUCT.md

Users: Reseller UMKM Indonesia, usia 20–40 tahun, akrab dengan TikTok & IG.
       Membaca di mobile, sering di sela-sela aktivitas.

Register: Dashboard operasional — bukan halaman pemasaran.
          Setiap layar harus menjawab satu pertanyaan: "apa yang harus aku lakukan sekarang?"

Brand voice: Kasual, suportif, langsung ke poin. Tidak formal, tidak hype berlebihan.
             Gunakan bahasa Indonesia yang natural.

Anti-references:
  - Purple gradient, glassmorphism, neon glow
  - "Boost your productivity" empty-state copy
  - Data table tanpa empty state atau loading state
  - Tombol yang muncul tapi tidak bisa diklik (→ pakai FeatureGate)
```

#### Command yang Relevan

| Command | Fungsi |
|---|---|
| `/impeccable polish` | Scan codebase, deteksi token & komponen existing, selaraskan desain |
| `/impeccable typeset` | Perbaiki hierarki tipografi (ukuran, weight, line-height) |
| `/impeccable colorize` | Pastikan palette konsisten dengan token Tailwind |
| `/impeccable layout` | Perbaiki spacing, alignment, dan grid |
| `/impeccable adapt` | Sesuaikan komponen untuk konteks spesifik (mobile, dark mode, dsb.) |
| `/impeccable document` | Generate/update DESIGN.md dari state codebase saat ini |
| `/impeccable detect src/` | Jalankan 45 aturan anti-slop — bisa dipakai di CI/PR check |

#### Integrasi CI (Opsional tapi Direkomendasikan)

Tambahkan step berikut di GitHub Actions untuk memblokir PR yang mengandung pola desain buruk:

```yaml
# .github/workflows/design-check.yml
- name: Impeccable design lint
  run: npx impeccable detect src/
  # Exit 1 jika ditemukan anti-pattern → PR tidak bisa merge
```

#### Aturan Tambahan untuk AI Agent

Setiap kali agent membuat atau mengubah komponen UI, agent **wajib**:

1. Membaca `DESIGN.md` dan `PRODUCT.md` sebelum menulis kode UI.
2. Menjalankan `/impeccable polish` setelah membuat halaman baru.
3. Tidak menggunakan pola yang ada di daftar anti-references `PRODUCT.md`.
4. Memastikan semua fitur yang bergantung integrasi eksternal dibungkus `<FeatureGate>` (lihat RULE-07).

---

*Versi 2.2 — Dokumen ini mencakup desain SaaS multi-tenant lengkap. Detail API contract, ERD lengkap, dan security audit checklist dapat dikembangkan pada fase technical spec berikutnya.*

---

## 15. AI Agent Autonomy Design

Sistem dirancang agar AI Agent dapat **beroperasi penuh tanpa intervensi manusia** selama kondisi normal. Berikut prinsip dan mekanismenya.

### 15.1 Prinsip Agentic Loop

Setiap engine berjalan dalam siklus otonom:

```
┌─────────────────────────────────────────────────────┐
│                   AGENTIC LOOP                       │
│                                                      │
│   OBSERVE → THINK → PLAN → ACT → EVALUATE → REPEAT  │
│                                                      │
│  OBSERVE  : Ambil data tren, event chat, performa    │
│  THINK    : LLM reasoning — apa yang harus dilakukan │
│  PLAN     : Susun langkah aksi (tool calls)          │
│  ACT      : Eksekusi: posting, reply, kirim link     │
│  EVALUATE : Cek hasil, update state, log outcome     │
│  REPEAT   : Jadwalkan siklus berikutnya              │
└─────────────────────────────────────────────────────┘
```

### 15.2 Tool Registry (Kemampuan AI Agent)

AI Agent memiliki akses ke tool berikut yang dipanggil sesuai kebutuhan:

| Tool | Fungsi | Dipanggil Oleh |
|---|---|---|
| `classify_intent` | Deteksi niat chat customer | Engagement Engine |
| `fetch_conversation_history` | Ambil histori chat customer | Engagement Engine |
| `search_product_knowledge` | RAG ke vector DB produk tenant | Engagement Engine |
| `send_reply` | Kirim balasan chat/komentar | Engagement Engine |
| `escalate_to_human` | Tandai percakapan untuk diambil alih manusia | Engagement Engine |
| `classify_lead` | Klasifikasi lead: hot / warm / cold | Lead Intelligence Engine |
| `log_lead` | Catat / update lead ke database | Lead Intelligence Engine |
| `check_feature_status` | Cek apakah fitur/integrasi aktif | Semua engine |

### 15.3 Decision Tree Otonom

AI Agent tidak memerlukan perintah manusia untuk mengeksekusi alur berikut:

```
[Confidence AI ≥ threshold] + [Fitur aktif] + [Dalam jam operasional] 
         → EKSEKUSI OTOMATIS

[Confidence AI < threshold] ATAU [Tenant aktifkan review mode]
         → MASUK ANTRIAN APPROVAL DASHBOARD

[Sentimen negatif] ATAU [Topik sensitif terdeteksi]
         → ESKALASI KE HUMAN INBOX

[Fitur tidak aktif / API key belum ada]
         → SKIP DENGAN GRACEFUL FALLBACK (lihat Bagian 16)
```

### 15.4 Self-Healing & Retry Logic

Jika sebuah tool call gagal, agent tidak berhenti — ia mengikuti logika berikut:

```
Attempt 1 → Gagal
  └─ Retry setelah 30 detik (exponential backoff)

Attempt 2 → Gagal
  └─ Retry setelah 2 menit

Attempt 3 → Gagal
  └─ Tandai task sebagai FAILED
  └─ Log error internal (TIDAK tampil ke user)
  └─ Notifikasi sistem (bukan raw error)
  └─ Lanjutkan task lain, skip task gagal
```

Platform API error umum dan cara agent menanganinya:

| Error | Respons Agent |
|---|---|
| Rate limit (429) | Backoff sesuai `Retry-After` header, lanjut setelah jeda |
| Token expired (401) | Auto-refresh token jika ada refresh_token, jika gagal → notifikasi tenant lewat dashboard |
| Platform down (5xx) | Retry 3x lalu reschedule task ke +1 jam |
| Konten ditolak platform | Log rejection reason, skip post, notifikasi tenant |

---

## 16. Graceful Feature Degradation

### 16.1 Prinsip Utama

> **Fitur yang belum dikonfigurasi tidak menghasilkan error — ia hanya tidak aktif, dan sistem tetap berjalan dengan fitur yang sudah siap.**

Tidak ada raw error, stack trace, atau pesan teknis yang boleh tampil ke tenant maupun end-user (customer di chat).

### 16.2 Feature Flag System

Setiap integrasi dan fitur memiliki status yang diperiksa sebelum eksekusi:

```typescript
// Tipe status fitur
type FeatureStatus = 
  | 'active'           // Aktif & siap digunakan
  | 'not_configured'   // API key / credential belum diisi
  | 'expired'          // Token kedaluwarsa, perlu reconnect
  | 'plan_locked'      // Fitur tidak tersedia di plan saat ini
  | 'quota_exceeded'   // Kuota bulan ini habis
  | 'disabled_by_user' // Dimatikan manual oleh tenant

// Setiap engine wajib panggil ini sebelum aksi
const status = await checkFeatureStatus(tenantId, 'instagram');

if (status !== 'active') {
  return gracefulSkip(status, 'instagram'); // TIDAK throw error
}
```

### 16.3 Peta Status Per Fitur

| Fitur / Integrasi | Trigger Nonaktif | Perilaku Sistem |
|---|---|---|
| **Facebook reply** | Token belum dikonfigurasi atau expired | Skip auto-reply, percakapan tetap dicatat di Inbox |
| **Lead classification** | Plan tidak support atau LLM gagal | Percakapan tetap masuk Inbox, lead tier default `cold` sampai retry berhasil |
| **RAG / product knowledge** | Belum ada produk di katalog | AI reply tanpa konteks produk spesifik, gunakan fallback prompt umum |

### 16.4 Pesan yang Ditampilkan ke Tenant (Dashboard)

Jika ada fitur tidak aktif, tenant melihat notifikasi **ramah dan actionable** — bukan error teknis:

```
┌──────────────────────────────────────────────────────────────┐
│  ⚠️  Instagram belum terhubung                                │
│                                                              │
│  Konten untuk Instagram akan disimpan sebagai draft sampai   │
│  kamu menghubungkan akunmu.                                  │
│                                                              │
│  [Hubungkan Instagram →]                    [Nanti saja]     │
└──────────────────────────────────────────────────────────────┘
```

```
┌──────────────────────────────────────────────────────────────┐
│  🔒  Fitur Product Discovery tersedia di plan Pro            │
│                                                              │
│  Upgrade untuk AI otomatis mencari produk trending           │
│  sesuai niche kamu setiap 6 jam.                             │
│                                                              │
│  [Upgrade ke Pro →]                         [Nanti saja]     │
└──────────────────────────────────────────────────────────────┘
```

```
┌──────────────────────────────────────────────────────────────┐
│  📊  Kuota AI Reply bulan ini sudah habis (500/500)          │
│                                                              │
│  AI auto-reply dijeda. Upgrade plan untuk melanjutkan,       │
│  atau tunggu reset di 1 Agustus 2026.                        │
│                                                              │
│  [Lihat Pilihan Plan →]                     [Nanti saja]     │
└──────────────────────────────────────────────────────────────┘
```

### 16.5 Pesan yang Ditampilkan ke Customer (End-User Chat)

Jika ada masalah teknis yang menyebabkan AI tidak bisa merespons optimal, customer **tidak pernah** melihat error teknis. Yang muncul adalah pesan netral:

```
✅ Normal:   "Halo kak! Boleh tanya lebih lanjut soal produknya? 😊"

✅ Fallback: "Halo! Terima kasih sudah menghubungi kami. 
              Tim kami akan segera membalas pesanmu ya 🙏"

❌ DILARANG: "Error 500: Internal Server Error"
❌ DILARANG: "TypeError: Cannot read property 'link' of undefined"
❌ DILARANG: "API rate limit exceeded: 429 Too Many Requests"
```

### 16.6 Error Boundary Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    REQUEST / EVENT MASUK                      │
└────────────────────────────┬─────────────────────────────────┘
                             │
                    ┌────────▼────────┐
                    │  FEATURE CHECK  │ ← checkFeatureStatus()
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
         [active]    [not configured]   [plan_locked /
              │         [expired]        quota_exceeded]
              │              │              │
         Jalankan      Graceful skip    Graceful skip
         Engine        + catat di log   + notif dashboard
              │              │              │
    ┌─────────▼──────────────▼──────────────▼─────────┐
    │              TRY / CATCH WRAPPER                  │
    │   Semua eksekusi engine dibungkus try-catch       │
    │   Error ditangkap → log internal → TIDAK throw    │
    └─────────────────────────┬────────────────────────┘
                              │
                   ┌──────────▼──────────┐
                   │   ERROR CLASSIFIER   │
                   │                     │
                   │ retryable?  → retry │
                   │ escalate?   → notif │
                   │ ignorable?  → skip  │
                   └─────────────────────┘
```

### 16.7 Onboarding Checklist (Aktivasi Bertahap)

Tenant melihat checklist ini saat pertama masuk dashboard. Fitur terkunci sampai langkah relevannya selesai:

```
SETUP AKUN
☐ 1. Hubungkan Facebook Page               → Buka: auto-reply komentar & DM
☐ 2. Isi nama toko & tone AI               → Buka: AI personalisasi
☐ 3. Tambahkan produk pertama              → Buka: RAG context untuk reply lebih akurat
☐ 4. Upgrade ke Starter / Pro              → Buka: kuota reply lebih tinggi, lead intelligence

SETIAP LANGKAH OPSIONAL — sistem tetap berjalan dengan fitur yang sudah aktif.
```

### 16.8 Logging Internal (Tidak Tampil ke User)

Semua error dan skip event dicatat di `system_logs` untuk debugging oleh Super Admin atau tim engineering — **tidak pernah diteruskan ke tenant atau customer:**

```sql
system_logs (
  id, tenant_id, engine, action, status,
  error_code,        -- kode internal (bukan raw stack trace)
  error_message,     -- deskripsi singkat internal
  context JSONB,     -- data konteks saat error terjadi
  created_at
)

-- Contoh record
{
  tenant_id: "abc-123",
  engine: "content_engine",
  action: "publish_post",
  status: "skipped",
  error_code: "INSTAGRAM_NOT_CONFIGURED",
  error_message: "Instagram credential not found for tenant",
  context: { product_id: "xyz", platform: "instagram" }
}
```

---

*Versi 2.2 — Penambahan: AI Agent Autonomy Design (Bagian 15) dan Graceful Feature Degradation (Bagian 16).*

*Versi 2.4 — Klarifikasi & penambahan: (1) RLS strategy diperbarui ke two-layer defense dengan `SET LOCAL` + catatan keamanan pooling (Bagian 4.1); (2) Catatan implementasi vector namespace via `tenant_id` filter (Bagian 4.3); (3) Tabel `users` dengan role `tenant_user` / `super_admin` (Bagian 7); (4) Tabel `product_embeddings` untuk pgvector RAG per tenant (Bagian 7); (5) Tabel `system_logs` untuk internal audit trail (Bagian 7).*

*Versi 2.6 — Landing page & public pages: Tambah Section 4.2 (Shared App Model), 4.3 (AI Context Per Tenant), 4.4 (Alur OAuth Facebook Page per tenant). Env vars baru: `META_REDIRECT_URI`, `META_OAUTH_SCOPES`. Domain sementara: `reseller.jawakoentji.my.id`.*

*Versi 2.7 — Revisi scope produk: (1) Hapus Content & Publishing Engine, Product Discovery Engine, Sales Conversion Engine dari roadmap; (2) Ganti Fase 3 menjadi Lead Intelligence Engine (klasifikasi hot/warm/cold); (3) Fase 4 menjadi SaaS Layer (billing, quota, Super Admin); (4) Update Ringkasan Eksekutif, Lingkup, arsitektur diagram, dashboard pages, onboarding flow, end-to-end contoh, tool registry, dan feature degradation map agar konsisten dengan scope baru.*

*Versi 2.5 — Fase 2 decisions: (1) Engagement Engine Fase 2 scope dipersempit ke Facebook + Messenger saja (Bagian 5.3); (2) Human takeover mechanic ditambahkan: kolom `is_human_takeover` di `conversations`, toggle via API, eskalasi otomatis, polling 10 detik di frontend (Bagian 5.3); (3) Topik eskalasi dikonfigurasi per tenant via `ai_config.escalation_topics` (Bagian 5.3 + skema tenants); (4) AI provider abstraksi: OpenRouter untuk dev/testing, OpenAI untuk production — swap via env vars tanpa ubah kode (Bagian 14.1, 14.3); (5) Skema `conversations` dan `customers` dilengkapi (Bagian 7); (6) Env vars baru: `OPENROUTER_API_KEY`, `OPENROUTER_BASE_URL`, `AI_MODEL_FAST`, `AI_MODEL_QUALITY` (Bagian 0.6).*
