# Fase 4b Subscription & Billing — Stripe Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tenant dapat upgrade plan via Stripe Checkout, backend menerima webhook konfirmasi payment dan mengupgrade plan, UI menampilkan plan saat ini dan tombol upgrade.

**Architecture:** Backend menyediakan endpoint untuk buat Stripe Checkout Session dan menerima Stripe webhook (`/webhooks/stripe`). Webhook diverifikasi dengan `STRIPE_WEBHOOK_SECRET`, lalu plan tenant diupdate di DB. Frontend menampilkan halaman Billing dengan plan aktif, tombol upgrade, dan redirect ke Stripe Checkout. Stripe webhook berjalan di luar `TenantContextMiddleware` (sama seperti `/webhooks/facebook`).

**Tech Stack:** `stripe` Python SDK, FastAPI, SQLAlchemy async, React 18 + Vite + Tailwind + shadcn/ui.

## Global Constraints

- Semua response backend pakai `APIResponse[T]` wrapper: `{"success": true, "data": ..., "message": ...}`
- Setiap query DB wajib filter `tenant_id` — tidak boleh query cross-tenant (RULE-03)
- Jangan buka `db.begin()` di router — `get_db_session` sudah buka transaksi
- Pydantic v2: pakai `model_validate()` bukan `from_orm()`, `model_dump()` bukan `dict()`
- `stripe` versi terbaru yang kompatibel dengan Python 3.12
- Semua path test: `backend/tests/test_<name>.py`
- Run test dari direktori `backend/`: `source .venv/bin/activate && pytest tests/<file> -v`
- Stripe webhook path `/webhooks/stripe` harus masuk `WEBHOOK_PATH_PREFIX` di `TenantContextMiddleware` agar bypass auth
- Plan values valid: `"free"`, `"starter"`, `"pro"`, `"enterprise"`
- `plan_expires_at` disimpan sebagai ISO string (`datetime.isoformat()`)

---

### Task 1: Install stripe + tambah Stripe config ke Settings

**Files:**
- Modify: `backend/pyproject.toml`
- Modify: `backend/app/core/config.py` (sudah ada `STRIPE_SECRET_KEY` dan `STRIPE_WEBHOOK_SECRET` — tidak perlu tambah field)

**Interfaces:**
- Produces: `stripe` package tersedia di `.venv`, `settings.STRIPE_SECRET_KEY` dan `settings.STRIPE_WEBHOOK_SECRET` dapat dibaca

- [ ] **Step 1: Tambah stripe ke dependencies**

Edit `backend/pyproject.toml`, tambah `"stripe>=10.0.0"` ke array `dependencies`:

```toml
dependencies = [
    "fastapi==0.115.0",
    "uvicorn[standard]==0.30.6",
    "sqlalchemy==2.0.35",
    "alembic==1.13.3",
    "asyncpg==0.29.0",
    "pgvector==0.3.2",
    "redis==5.1.1",
    "celery==5.4.0",
    "pydantic==2.9.2",
    "pydantic-settings==2.5.2",
    "python-jose[cryptography]==3.3.0",
    "passlib[bcrypt]==1.7.4",
    "bcrypt==4.0.1",
    "cryptography==43.0.1",
    "httpx==0.27.2",
    "openai==1.51.0",
    "email-validator==2.2.0",
    "stripe>=10.0.0",
]
```

- [ ] **Step 2: Install dependency**

```bash
cd backend
source .venv/bin/activate
pip install stripe
```

Expected: `Successfully installed stripe-...`

- [ ] **Step 3: Verifikasi import**

```bash
python -c "import stripe; print(stripe.__version__)"
```

Expected: prints version number, no error.

- [ ] **Step 4: Commit**

```bash
git add backend/pyproject.toml
git commit -m "feat: add stripe dependency"
```

---

### Task 2: Tambah kolom stripe_customer_id ke Tenant model + migration

**Files:**
- Modify: `backend/app/models/tenant.py`
- Create: `backend/alembic/versions/<auto>_add_stripe_customer_id_to_tenants.py`

**Interfaces:**
- Consumes: `Tenant` model dari `backend/app/models/tenant.py`
- Produces: `Tenant.stripe_customer_id: Mapped[str | None]` tersedia

- [ ] **Step 1: Tambah kolom ke Tenant model**

Edit `backend/app/models/tenant.py`:

```python
import uuid

from sqlalchemy import JSON, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

class Tenant(Base, TimestampMixin):
    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    plan: Mapped[str] = mapped_column(String(50), default="free", nullable=False)
    plan_expires_at: Mapped[str | None] = mapped_column(nullable=True)
    stripe_customer_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ai_config: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    users: Mapped[list["User"]] = relationship("User", back_populates="tenant")
```

- [ ] **Step 2: Generate migration**

```bash
cd backend
source .venv/bin/activate
alembic revision --autogenerate -m "add_stripe_customer_id_to_tenants"
```

Expected: creates file `backend/alembic/versions/<hash>_add_stripe_customer_id_to_tenants.py`

- [ ] **Step 3: Periksa migration yang digenerate**

Buka file migration yang baru dibuat, pastikan `upgrade()` berisi:
```python
op.add_column('tenants', sa.Column('stripe_customer_id', sa.String(length=100), nullable=True))
```

Dan `downgrade()` berisi:
```python
op.drop_column('tenants', 'stripe_customer_id')
```

- [ ] **Step 4: Run migration**

```bash
alembic upgrade head
```

Expected: `Running upgrade ... -> <hash>, add_stripe_customer_id_to_tenants`

- [ ] **Step 5: Commit**

```bash
git add backend/app/models/tenant.py backend/alembic/versions/
git commit -m "feat: add stripe_customer_id to tenants"
```

---

### Task 3: Billing service — plan definitions, create Stripe Checkout session, handle webhook

**Files:**
- Create: `backend/app/services/billing_service.py`
- Create: `backend/tests/test_billing_service.py`

**Interfaces:**
- Consumes: `settings.STRIPE_SECRET_KEY`, `settings.STRIPE_WEBHOOK_SECRET`, `Tenant` model (dengan `stripe_customer_id`, `plan`, `plan_expires_at`, `email`)
- Produces:
  - `PLAN_PRICES: dict[str, str]` — map plan → Stripe Price ID
  - `create_checkout_session(tenant_id, plan, success_url, cancel_url, db) -> str` — returns Stripe Checkout URL
  - `handle_stripe_webhook(payload: bytes, sig_header: str, db) -> None` — processes `checkout.session.completed`

- [ ] **Step 1: Tulis failing tests**

Buat `backend/tests/test_billing_service.py`:

```python
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.billing_service import create_checkout_session, handle_stripe_webhook


def _mock_db():
    db = MagicMock()
    db.execute = AsyncMock()
    db.flush = AsyncMock()
    db.add = MagicMock()
    return db


def _make_tenant(tenant_id: uuid.UUID, plan: str = "free"):
    from app.models.tenant import Tenant
    t = Tenant(
        id=tenant_id,
        name="Test Tenant",
        email="test@example.com",
        plan=plan,
        ai_config={},
    )
    return t


@pytest.mark.asyncio
async def test_create_checkout_session_returns_url():
    tenant_id = str(uuid.uuid4())
    db = _mock_db()

    tenant = _make_tenant(uuid.UUID(tenant_id))
    execute_result = MagicMock()
    execute_result.scalar_one_or_none.return_value = tenant
    db.execute.return_value = execute_result

    mock_session = MagicMock()
    mock_session.url = "https://checkout.stripe.com/pay/cs_test_abc"

    with patch("stripe.checkout.Session.create", return_value=mock_session):
        with patch("stripe.Customer.create", return_value=MagicMock(id="cus_test123")):
            url = await create_checkout_session(
                tenant_id=tenant_id,
                plan="starter",
                success_url="https://app.test/billing?success=1",
                cancel_url="https://app.test/billing?cancel=1",
                db=db,
            )

    assert url == "https://checkout.stripe.com/pay/cs_test_abc"


@pytest.mark.asyncio
async def test_create_checkout_session_raises_if_tenant_not_found():
    tenant_id = str(uuid.uuid4())
    db = _mock_db()
    execute_result = MagicMock()
    execute_result.scalar_one_or_none.return_value = None
    db.execute.return_value = execute_result

    with pytest.raises(ValueError, match="Tenant tidak ditemukan"):
        await create_checkout_session(
            tenant_id=tenant_id,
            plan="starter",
            success_url="https://app.test/billing?success=1",
            cancel_url="https://app.test/billing?cancel=1",
            db=db,
        )


@pytest.mark.asyncio
async def test_handle_webhook_upgrades_plan():
    db = _mock_db()
    tenant_id = str(uuid.uuid4())
    tenant = _make_tenant(uuid.UUID(tenant_id))

    execute_result = MagicMock()
    execute_result.scalar_one_or_none.return_value = tenant
    db.execute.return_value = execute_result

    mock_event = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "metadata": {"tenant_id": tenant_id, "plan": "pro"},
                "customer": "cus_test123",
            }
        },
    }

    with patch("stripe.Webhook.construct_event", return_value=mock_event):
        await handle_stripe_webhook(b"payload", "sig_header", db)

    assert tenant.plan == "pro"
    assert tenant.stripe_customer_id == "cus_test123"
    assert tenant.plan_expires_at is not None


@pytest.mark.asyncio
async def test_handle_webhook_ignores_unknown_event():
    db = _mock_db()
    mock_event = {"type": "payment_intent.created", "data": {"object": {}}}

    with patch("stripe.Webhook.construct_event", return_value=mock_event):
        await handle_stripe_webhook(b"payload", "sig_header", db)

    db.execute.assert_not_called()
```

- [ ] **Step 2: Run test — pastikan FAIL**

```bash
cd backend && source .venv/bin/activate
pytest tests/test_billing_service.py -v
```

Expected: `ImportError` atau `ModuleNotFoundError` karena `billing_service` belum ada.

- [ ] **Step 3: Implementasi billing_service.py**

Buat `backend/app/services/billing_service.py`:

```python
import logging
import uuid
from datetime import datetime, timedelta, timezone

import stripe
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.tenant import Tenant

logger = logging.getLogger(__name__)

PLAN_PRICES: dict[str, str] = {
    "starter": "price_REPLACE_WITH_STRIPE_PRICE_ID_STARTER",
    "pro": "price_REPLACE_WITH_STRIPE_PRICE_ID_PRO",
    "enterprise": "price_REPLACE_WITH_STRIPE_PRICE_ID_ENTERPRISE",
}

PLAN_DURATION_DAYS: dict[str, int] = {
    "starter": 30,
    "pro": 30,
    "enterprise": 365,
}


async def _get_tenant(tenant_id: str, db: AsyncSession) -> Tenant | None:
    result = await db.execute(select(Tenant).where(Tenant.id == uuid.UUID(tenant_id)))
    return result.scalar_one_or_none()


async def create_checkout_session(
    tenant_id: str,
    plan: str,
    success_url: str,
    cancel_url: str,
    db: AsyncSession,
) -> str:
    settings = get_settings()
    stripe.api_key = settings.STRIPE_SECRET_KEY

    tenant = await _get_tenant(tenant_id, db)
    if tenant is None:
        raise ValueError("Tenant tidak ditemukan")

    if plan not in PLAN_PRICES:
        raise ValueError(f"Plan tidak valid: {plan}")

    # Buat atau ambil Stripe Customer
    if tenant.stripe_customer_id:
        customer_id = tenant.stripe_customer_id
    else:
        customer = stripe.Customer.create(
            email=tenant.email,
            name=tenant.name,
            metadata={"tenant_id": tenant_id},
        )
        customer_id = customer.id
        tenant.stripe_customer_id = customer_id

    session = stripe.checkout.Session.create(
        customer=customer_id,
        payment_method_types=["card"],
        line_items=[{"price": PLAN_PRICES[plan], "quantity": 1}],
        mode="subscription",
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={"tenant_id": tenant_id, "plan": plan},
    )

    logger.info(
        "Stripe checkout session created",
        extra={"tenant_id": tenant_id, "plan": plan, "session_id": session.id},
    )
    return session.url


async def handle_stripe_webhook(
    payload: bytes,
    sig_header: str,
    db: AsyncSession,
) -> None:
    settings = get_settings()
    stripe.api_key = settings.STRIPE_SECRET_KEY

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except stripe.error.SignatureVerificationError:
        logger.warning("Stripe webhook signature invalid")
        raise ValueError("Signature tidak valid")

    if event["type"] != "checkout.session.completed":
        logger.debug("Stripe webhook ignored", extra={"event_type": event["type"]})
        return

    session_obj = event["data"]["object"]
    metadata = session_obj.get("metadata", {})
    tenant_id = metadata.get("tenant_id")
    plan = metadata.get("plan")
    customer_id = session_obj.get("customer")

    if not tenant_id or not plan:
        logger.error("Stripe webhook missing metadata", extra={"metadata": metadata})
        return

    tenant = await _get_tenant(tenant_id, db)
    if tenant is None:
        logger.error("Stripe webhook tenant not found", extra={"tenant_id": tenant_id})
        return

    duration = PLAN_DURATION_DAYS.get(plan, 30)
    expires_at = datetime.now(timezone.utc) + timedelta(days=duration)

    tenant.plan = plan
    tenant.plan_expires_at = expires_at.isoformat()
    if customer_id:
        tenant.stripe_customer_id = customer_id

    logger.info(
        "Tenant plan upgraded via Stripe",
        extra={"tenant_id": tenant_id, "plan": plan, "expires_at": expires_at.isoformat()},
    )
```

- [ ] **Step 4: Run test — pastikan PASS**

```bash
pytest tests/test_billing_service.py -v
```

Expected:
```
test_create_checkout_session_returns_url PASSED
test_create_checkout_session_raises_if_tenant_not_found PASSED
test_handle_webhook_upgrades_plan PASSED
test_handle_webhook_ignores_unknown_event PASSED
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/billing_service.py backend/tests/test_billing_service.py
git commit -m "feat: billing service — Stripe checkout session + webhook handler"
```

---

### Task 4: Billing schemas

**Files:**
- Create: `backend/app/schemas/billing.py`

**Interfaces:**
- Produces:
  - `CreateCheckoutSessionRequest(plan: str, success_url: str, cancel_url: str)`
  - `BillingStatusResponse(plan: str, plan_expires_at: str | None, stripe_customer_id: str | None)`

- [ ] **Step 1: Buat billing schema**

Buat `backend/app/schemas/billing.py`:

```python
from pydantic import BaseModel, Field


class CreateCheckoutSessionRequest(BaseModel):
    plan: str = Field(..., pattern="^(starter|pro|enterprise)$")
    success_url: str = Field(..., min_length=10)
    cancel_url: str = Field(..., min_length=10)


class CheckoutSessionResponse(BaseModel):
    checkout_url: str


class BillingStatusResponse(BaseModel):
    plan: str
    plan_expires_at: str | None
    stripe_customer_id: str | None
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/schemas/billing.py
git commit -m "feat: billing schemas"
```

---

### Task 5: Billing router — GET /billing/status, POST /billing/checkout, POST /webhooks/stripe

**Files:**
- Create: `backend/app/routers/billing.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/middleware/tenant_context.py`
- Create: `backend/tests/test_billing_router.py`

**Interfaces:**
- Consumes:
  - `create_checkout_session(tenant_id, plan, success_url, cancel_url, db) -> str`
  - `handle_stripe_webhook(payload, sig_header, db) -> None`
  - `BillingStatusResponse`, `CreateCheckoutSessionRequest`, `CheckoutSessionResponse`
- Produces:
  - `GET /api/v1/billing/status` → `APIResponse[BillingStatusResponse]`
  - `POST /api/v1/billing/checkout` → `APIResponse[CheckoutSessionResponse]`
  - `POST /webhooks/stripe` → `{"received": true}` (no auth)

- [ ] **Step 1: Tulis failing tests**

Buat `backend/tests/test_billing_router.py`:

```python
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


def _auth_headers(client):
    """Helper: register + login, return tenant_id."""
    reg = client.post("/api/v1/auth/register", json={
        "name": "Billing Test",
        "email": "billing@test.com",
        "password": "Test1234!",
    })
    assert reg.status_code == 200
    return {}  # cookie-based auth, no headers needed


def test_billing_status_requires_auth(client):
    res = client.get("/api/v1/billing/status")
    assert res.status_code == 401


def test_billing_status_returns_plan(client):
    client.post("/api/v1/auth/register", json={
        "name": "Billing Test",
        "email": "billingx@test.com",
        "password": "Test1234!",
    })
    client.post("/api/v1/auth/login", json={
        "email": "billingx@test.com",
        "password": "Test1234!",
    })
    res = client.get("/api/v1/billing/status")
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["data"]["plan"] == "free"


def test_stripe_webhook_returns_200_on_valid_payload(client):
    mock_event = {
        "type": "checkout.session.completed",
        "data": {"object": {"metadata": {}, "customer": None}},
    }
    with patch("app.routers.billing.handle_stripe_webhook", new_callable=AsyncMock) as mock_handler:
        mock_handler.return_value = None
        res = client.post(
            "/webhooks/stripe",
            content=b'{"type":"checkout.session.completed"}',
            headers={"stripe-signature": "t=1,v1=test"},
        )
    assert res.status_code == 200
    assert res.json() == {"received": True}


def test_stripe_webhook_returns_400_on_invalid_signature(client):
    with patch("app.routers.billing.handle_stripe_webhook", new_callable=AsyncMock) as mock_handler:
        mock_handler.side_effect = ValueError("Signature tidak valid")
        res = client.post(
            "/webhooks/stripe",
            content=b'{"type":"checkout.session.completed"}',
            headers={"stripe-signature": "bad-sig"},
        )
    assert res.status_code == 400
```

- [ ] **Step 2: Run test — pastikan FAIL**

```bash
cd backend && source .venv/bin/activate
pytest tests/test_billing_router.py -v
```

Expected: 404 pada semua billing endpoints (router belum ada).

- [ ] **Step 3: Buat billing router**

Buat `backend/app/routers/billing.py`:

```python
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.schemas.base import APIResponse
from app.schemas.billing import (
    BillingStatusResponse,
    CheckoutSessionResponse,
    CreateCheckoutSessionRequest,
)
from app.services.billing_service import create_checkout_session, handle_stripe_webhook

logger = logging.getLogger(__name__)

router = APIRouter(tags=["billing"])


@router.get("/api/v1/billing/status", response_model=APIResponse[BillingStatusResponse])
async def get_billing_status(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    tenant_id: str = request.state.tenant_id
    from sqlalchemy import select
    from app.models.tenant import Tenant
    import uuid
    result = await db.execute(select(Tenant).where(Tenant.id == uuid.UUID(tenant_id)))
    tenant = result.scalar_one_or_none()
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant tidak ditemukan.")
    return APIResponse(data=BillingStatusResponse(
        plan=tenant.plan,
        plan_expires_at=tenant.plan_expires_at,
        stripe_customer_id=tenant.stripe_customer_id,
    ))


@router.post("/api/v1/billing/checkout", response_model=APIResponse[CheckoutSessionResponse])
async def create_checkout(
    body: CreateCheckoutSessionRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    tenant_id: str = request.state.tenant_id
    try:
        url = await create_checkout_session(
            tenant_id=tenant_id,
            plan=body.plan,
            success_url=body.success_url,
            cancel_url=body.cancel_url,
            db=db,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return APIResponse(
        data=CheckoutSessionResponse(checkout_url=url),
        message="Checkout session berhasil dibuat.",
    )


@router.post("/webhooks/stripe")
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")
    try:
        await handle_stripe_webhook(payload, sig_header, db)
    except ValueError as e:
        logger.warning("Stripe webhook rejected", extra={"reason": str(e)})
        raise HTTPException(status_code=400, detail=str(e))
    return JSONResponse({"received": True})
```

- [ ] **Step 4: Register router di main.py**

Edit `backend/app/main.py`:

```python
from app.routers import auth, billing, conversations, features, leads, products, settings, webhooks
```

Dan di bagian Routers, tambah:
```python
app.include_router(billing.router)
```

- [ ] **Step 5: Tambah `/webhooks/stripe` ke middleware whitelist**

Edit `backend/app/middleware/tenant_context.py` — `WEBHOOK_PATH_PREFIX` sudah cover semua `/webhooks/` prefix, cek baris:

```python
WEBHOOK_PATH_PREFIX = "/webhooks"
```

Kalau sudah ada seperti itu, tidak perlu ubah apapun — `/webhooks/stripe` sudah bypass auth.

- [ ] **Step 6: Run test — pastikan PASS**

```bash
pytest tests/test_billing_router.py -v
```

Expected:
```
test_billing_status_requires_auth PASSED
test_billing_status_returns_plan PASSED
test_stripe_webhook_returns_200_on_valid_payload PASSED
test_stripe_webhook_returns_400_on_invalid_signature PASSED
```

- [ ] **Step 7: Run full test suite — pastikan tidak ada regresi**

```bash
pytest tests/ -v --tb=short 2>&1 | tail -20
```

Expected: semua test sebelumnya tetap PASS.

- [ ] **Step 8: Commit**

```bash
git add backend/app/routers/billing.py backend/app/main.py backend/app/middleware/tenant_context.py backend/tests/test_billing_router.py
git commit -m "feat: billing router — status, checkout, stripe webhook"
```

---

### Task 6: Frontend — useBilling hook + halaman Billing

**Files:**
- Create: `frontend/src/hooks/useBilling.ts`
- Create: `frontend/src/pages/Billing.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/AppLayout.tsx`

**Interfaces:**
- Consumes:
  - `GET /api/v1/billing/status` → `{ plan, plan_expires_at, stripe_customer_id }`
  - `POST /api/v1/billing/checkout` body: `{ plan, success_url, cancel_url }` → `{ checkout_url }`
- Produces: halaman `/billing` yang menampilkan plan aktif + tombol upgrade per plan

- [ ] **Step 1: Buat useBilling hook**

Buat `frontend/src/hooks/useBilling.ts`:

```typescript
import { useCallback, useEffect, useState } from "react";
import api from "@/lib/api";

export interface BillingStatus {
  plan: string;
  plan_expires_at: string | null;
  stripe_customer_id: string | null;
}

const PLAN_LABELS: Record<string, string> = {
  free: "Gratis",
  starter: "Starter",
  pro: "Pro",
  enterprise: "Enterprise",
};

export function useBilling() {
  const [status, setStatus] = useState<BillingStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [redirecting, setRedirecting] = useState(false);

  const fetchStatus = useCallback(async () => {
    setIsLoading(true);
    try {
      const res = await api.get<{ data: BillingStatus }>("/billing/status");
      setStatus(res.data.data);
    } catch {
      setError("Gagal memuat info billing.");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStatus();
  }, [fetchStatus]);

  async function startCheckout(plan: string): Promise<void> {
    setRedirecting(true);
    try {
      const origin = window.location.origin;
      const res = await api.post<{ data: { checkout_url: string } }>("/billing/checkout", {
        plan,
        success_url: `${origin}/billing?success=1`,
        cancel_url: `${origin}/billing?cancel=1`,
      });
      window.location.href = res.data.data.checkout_url;
    } catch {
      setError("Gagal membuat checkout. Coba lagi.");
      setRedirecting(false);
    }
  }

  return { status, isLoading, error, redirecting, startCheckout, planLabel: PLAN_LABELS };
}
```

- [ ] **Step 2: Buat halaman Billing**

Buat `frontend/src/pages/Billing.tsx`:

```tsx
import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { useBilling } from "@/hooks/useBilling";
import AppLayout from "@/components/AppLayout";

const PLANS = [
  {
    key: "starter",
    label: "Starter",
    price: "Rp 99.000 / bulan",
    features: ["Instagram & TikTok reply", "Content publish", "Product discovery"],
  },
  {
    key: "pro",
    label: "Pro",
    price: "Rp 299.000 / bulan",
    features: [
      "Semua fitur Starter",
      "Facebook & WhatsApp reply",
      "Lead classification",
      "Analytics",
    ],
  },
  {
    key: "enterprise",
    label: "Enterprise",
    price: "Hubungi kami",
    features: ["Semua fitur Pro", "Unlimited channels", "Dedicated support", "Custom SLA"],
  },
] as const;

function formatExpiry(iso: string | null) {
  if (!iso) return null;
  return new Date(iso).toLocaleDateString("id-ID", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

export default function Billing() {
  const { status, isLoading, error, redirecting, startCheckout, planLabel } = useBilling();
  const [searchParams] = useSearchParams();
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    if (searchParams.get("success") === "1") {
      setNotice("Pembayaran berhasil! Plan akan aktif dalam beberapa menit.");
    } else if (searchParams.get("cancel") === "1") {
      setNotice("Checkout dibatalkan. Plan tidak berubah.");
    }
  }, [searchParams]);

  return (
    <AppLayout>
      <div className="mx-auto max-w-4xl p-6">
        <h1 className="mb-1 text-xl font-semibold text-slate-900">Billing & Plan</h1>
        <p className="mb-6 text-sm text-slate-500">Pilih plan yang sesuai kebutuhan bisnis kamu.</p>

        {notice && (
          <div className="mb-6 rounded-lg border border-teal-200 bg-teal-50 px-4 py-3 text-sm text-teal-800">
            {notice}
          </div>
        )}

        {error && (
          <div className="mb-6 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        {/* Current plan */}
        {!isLoading && status && (
          <div className="mb-6 rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
            <p className="text-xs text-slate-400 mb-1">Plan aktif</p>
            <div className="flex items-center gap-3">
              <span className="text-lg font-semibold text-slate-900">
                {planLabel[status.plan] ?? status.plan}
              </span>
              {status.plan !== "free" && status.plan_expires_at && (
                <span className="text-xs text-slate-500">
                  aktif hingga {formatExpiry(status.plan_expires_at)}
                </span>
              )}
              {status.plan === "free" && (
                <span className="rounded-md bg-slate-100 px-2 py-0.5 text-xs text-slate-500">
                  Gratis
                </span>
              )}
            </div>
          </div>
        )}

        {isLoading && (
          <div className="mb-6 h-16 rounded-lg border border-slate-200 bg-white animate-pulse" />
        )}

        {/* Plan cards */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          {PLANS.map((plan) => {
            const isCurrent = status?.plan === plan.key;
            return (
              <div
                key={plan.key}
                className={[
                  "flex flex-col rounded-lg border bg-white p-5 shadow-sm",
                  isCurrent ? "border-[#0d7a8a] ring-1 ring-[#0d7a8a]/30" : "border-slate-200",
                ].join(" ")}
              >
                <div className="mb-3 flex items-center justify-between">
                  <h2 className="font-semibold text-slate-900">{plan.label}</h2>
                  {isCurrent && (
                    <span className="rounded-md bg-[#0d7a8a]/10 px-2 py-0.5 text-xs font-medium text-[#0d7a8a]">
                      Aktif
                    </span>
                  )}
                </div>
                <p className="mb-4 text-sm font-medium text-slate-700">{plan.price}</p>
                <ul className="mb-6 flex-1 space-y-1.5">
                  {plan.features.map((f) => (
                    <li key={f} className="flex items-start gap-2 text-sm text-slate-600">
                      <span className="mt-0.5 text-[#0d7a8a]" aria-hidden="true">✓</span>
                      {f}
                    </li>
                  ))}
                </ul>
                <Button
                  size="sm"
                  disabled={isCurrent || redirecting || plan.key === "enterprise"}
                  onClick={() => plan.key !== "enterprise" && startCheckout(plan.key)}
                  className={
                    isCurrent
                      ? "bg-slate-100 text-slate-400 cursor-default"
                      : "bg-[#0d7a8a] hover:bg-[#0b6b7a] text-white"
                  }
                >
                  {plan.key === "enterprise"
                    ? "Hubungi Kami"
                    : isCurrent
                    ? "Plan Aktif"
                    : redirecting
                    ? "Mengalihkan..."
                    : "Pilih Plan"}
                </Button>
              </div>
            );
          })}
        </div>
      </div>
    </AppLayout>
  );
}
```

- [ ] **Step 3: Tambah route /billing di App.tsx**

Edit `frontend/src/App.tsx` — tambah import dan route:

```tsx
import Billing from "@/pages/Billing";
```

Di dalam `<Routes>`, tambah setelah route settings:
```tsx
<Route
  path="/billing"
  element={
    <ProtectedRoute>
      <Billing />
    </ProtectedRoute>
  }
/>
```

- [ ] **Step 4: Tambah menu Billing di AppLayout sidebar**

Edit `frontend/src/components/AppLayout.tsx` — tambah item ke `NAV_ITEMS` array setelah Pengaturan:

```tsx
{
  to: "/billing",
  label: "Billing",
  icon: (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <rect x="1" y="4" width="22" height="16" rx="2" ry="2" />
      <line x1="1" y1="10" x2="23" y2="10" />
    </svg>
  ),
},
```

- [ ] **Step 5: Build frontend — pastikan tidak ada TS error**

```bash
cd frontend && npm run build 2>&1 | tail -10
```

Expected: `✓ built in ...ms` tanpa error TypeScript.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/hooks/useBilling.ts frontend/src/pages/Billing.tsx frontend/src/App.tsx frontend/src/components/AppLayout.tsx
git commit -m "feat: billing page — plan status, Stripe checkout redirect"
```

---

### Task 7: Konfigurasi PLAN_PRICES dengan Stripe Price IDs nyata

**Files:**
- Modify: `backend/app/services/billing_service.py` (ganti placeholder Price IDs)
- Modify: `backend/.env` (tambah env vars opsional untuk Price IDs)

**Interfaces:**
- Consumes: Stripe Dashboard → Products → Price IDs untuk masing-masing plan

> **Catatan:** Task ini dijalankan manual — butuh akses ke Stripe Dashboard untuk membuat Products dan mendapatkan Price IDs.

- [ ] **Step 1: Buat Products di Stripe Dashboard**

Masuk ke [Stripe Dashboard](https://dashboard.stripe.com) → Products → Add product:
1. **Starter** — Recurring, Rp 99.000/month → copy Price ID (`price_xxx`)
2. **Pro** — Recurring, Rp 299.000/month → copy Price ID (`price_xxx`)
3. **Enterprise** — skip (manual negotiation)

- [ ] **Step 2: Update PLAN_PRICES di billing_service.py**

Ganti placeholder di `backend/app/services/billing_service.py`:

```python
PLAN_PRICES: dict[str, str] = {
    "starter": "price_ACTUAL_STARTER_ID",   # ganti dengan Price ID dari Stripe
    "pro": "price_ACTUAL_PRO_ID",            # ganti dengan Price ID dari Stripe
    "enterprise": "price_ACTUAL_ENT_ID",    # opsional
}
```

- [ ] **Step 3: Pastikan .env terisi**

Cek `backend/.env` memiliki:
```
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
```

- [ ] **Step 4: Test end-to-end dengan Stripe CLI (opsional)**

Install [Stripe CLI](https://stripe.com/docs/stripe-cli), lalu:
```bash
stripe listen --forward-to localhost:8000/webhooks/stripe
```

Buka browser → `/billing` → klik "Pilih Plan" → complete Stripe test checkout → verifikasi plan berubah di DB.

- [ ] **Step 5: Commit jika ada perubahan**

```bash
git add backend/app/services/billing_service.py
git commit -m "feat: wire Stripe Price IDs for starter and pro plans"
```

---

## Self-Review

**1. Spec coverage:**
- ✅ Plan model (free/starter/pro/enterprise) — sudah ada di `feature_flags.py`, Task 2 tambah `stripe_customer_id`
- ✅ Stripe Checkout: buat session → redirect ke Stripe — Task 3 + 5 + 6
- ✅ Webhook konfirmasi payment → upgrade plan — Task 3 + 5
- ✅ Invoice & notifikasi email (Resend) — **TIDAK dicover dalam plan ini** — Resend email adalah subsystem terpisah, disarankan dibuat plan terpisah setelah billing berjalan

**2. Placeholder scan:** Tidak ada TBD/TODO. Task 7 Step 1-2 butuh manual action dari user (Stripe Dashboard) — ini bukan placeholder, ini memang manual step yang tidak bisa diotomasi.

**3. Type consistency:**
- `create_checkout_session` return type `str` (URL) — konsisten di billing_service, router, dan hook
- `handle_stripe_webhook(payload: bytes, sig_header: str, db) -> None` — konsisten di service dan router
- `BillingStatus.plan` adalah `str` — konsisten dengan `Tenant.plan: Mapped[str]`
