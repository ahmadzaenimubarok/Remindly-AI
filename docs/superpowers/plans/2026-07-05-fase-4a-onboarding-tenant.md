# Fase 4a — Onboarding Tenant Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tenant bisa self-serve: daftarkan produk via API, simpan Facebook Page token via UI, dan melewati onboarding flow terarah setelah register.

**Architecture:** Tambah router `/products` (CRUD) dan `/settings` (simpan FB token). Frontend tambah halaman Products, Settings, dan onboarding wizard setelah login pertama kali. Token FB dienkripsi dengan Fernet sebelum disimpan ke `tenant_credentials`.

**Tech Stack:** FastAPI + SQLAlchemy async, Pydantic v2, React 18 + Vite + Tailwind + shadcn/ui, Axios (cookie-based auth), Cryptography (Fernet), httpx (sync client untuk Celery worker).

## Global Constraints

- Semua endpoint proteksi via `TenantContextMiddleware` — `request.state.tenant_id` selalu tersedia
- Multi-tenant isolation WAJIB: semua query filter `WHERE tenant_id = ?` (RULE-03 SDD)
- Response format: `APIResponse[T]` dari `app.schemas.base` — `{"success": true, "data": ..., "message": ...}`
- Validasi input WAJIB pakai Pydantic model (`class XxxRequest(BaseModel)`), bukan `body: dict`
- Token FB dienkripsi dengan `encrypt_credential()` dari `app.core.security`, dekripsi dengan `decrypt_credential()`
- Frontend call API via `import api from "@/lib/api"` (Axios instance, baseURL `/api/v1`, withCredentials)
- Test file masuk `backend/tests/`, jalankan dengan `pytest backend/tests/` dari root project

---

## File Structure

**Backend — baru:**
- `backend/app/schemas/product.py` — `CreateProductRequest`, `UpdateProductRequest`, `ProductResponse`
- `backend/app/services/product_service.py` — `create_product`, `list_products`, `update_product`, `delete_product`
- `backend/app/routers/products.py` — router `/api/v1/products`
- `backend/app/schemas/settings.py` — `SaveFBTokenRequest`, `SettingsResponse`
- `backend/app/services/settings_service.py` — `save_fb_token`, `get_settings_status`
- `backend/app/routers/settings.py` — router `/api/v1/settings`
- `backend/tests/test_product_service.py`
- `backend/tests/test_settings_service.py`

**Backend — modifikasi:**
- `backend/app/main.py` — register router `products` dan `settings`

**Frontend — baru:**
- `frontend/src/hooks/useProducts.ts` — fetch + mutate products
- `frontend/src/hooks/useSettings.ts` — fetch settings status + save FB token
- `frontend/src/pages/Products.tsx` — halaman daftar + tambah + edit + hapus produk
- `frontend/src/pages/Settings.tsx` — halaman connect Facebook Page

**Frontend — modifikasi:**
- `frontend/src/App.tsx` — tambah route `/products` dan `/settings`

---

## Task 1: Schema & Service — Product CRUD

**Files:**
- Create: `backend/app/schemas/product.py`
- Create: `backend/app/services/product_service.py`
- Create: `backend/tests/test_product_service.py`

**Interfaces:**
- Produces:
  - `create_product(tenant_id: str, body: CreateProductRequest, db: AsyncSession) -> Product`
  - `list_products(tenant_id: str, db: AsyncSession) -> list[Product]`
  - `update_product(product_id: uuid.UUID, tenant_id: str, body: UpdateProductRequest, db: AsyncSession) -> Product | None`
  - `delete_product(product_id: uuid.UUID, tenant_id: str, db: AsyncSession) -> bool`
  - `ProductResponse` — schema Pydantic untuk response

- [ ] **Step 1: Tulis test yang gagal**

```python
# backend/tests/test_product_service.py
import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.schemas.product import CreateProductRequest, UpdateProductRequest
from app.services.product_service import (
    create_product,
    delete_product,
    list_products,
    update_product,
)


def _mock_db():
    db = MagicMock()
    db.execute = AsyncMock()
    db.flush = AsyncMock()
    db.add = MagicMock()
    return db


def _make_product(tenant_id: uuid.UUID):
    from app.models.product import Product
    p = Product(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        name="Produk Test",
        base_price=Decimal("50000"),
        status="active",
    )
    return p


@pytest.mark.asyncio
async def test_create_product_returns_product():
    tenant_id = str(uuid.uuid4())
    db = _mock_db()
    db.flush = AsyncMock()

    body = CreateProductRequest(name="Sepatu Lari", base_price=Decimal("150000"))

    with pytest.MonkeyPatch().context() as mp:
        from app.models.product import Product as PModel
        result = await create_product(tenant_id, body, db)

    assert result.name == "Sepatu Lari"
    assert result.tenant_id == uuid.UUID(tenant_id)
    db.add.assert_called_once()
    db.flush.assert_called_once()


@pytest.mark.asyncio
async def test_list_products_filters_by_tenant():
    tenant_id = str(uuid.uuid4())
    other_tenant_id = str(uuid.uuid4())
    db = _mock_db()

    own_product = _make_product(uuid.UUID(tenant_id))
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = [own_product]
    execute_result = MagicMock()
    execute_result.scalars.return_value = scalars_mock
    db.execute.return_value = execute_result

    products = await list_products(tenant_id, db)
    assert len(products) == 1
    assert products[0].tenant_id == uuid.UUID(tenant_id)


@pytest.mark.asyncio
async def test_update_product_returns_none_if_not_found():
    tenant_id = str(uuid.uuid4())
    db = _mock_db()
    execute_result = MagicMock()
    execute_result.scalar_one_or_none.return_value = None
    db.execute.return_value = execute_result

    result = await update_product(uuid.uuid4(), tenant_id, UpdateProductRequest(name="X"), db)
    assert result is None


@pytest.mark.asyncio
async def test_delete_product_returns_false_if_not_found():
    tenant_id = str(uuid.uuid4())
    db = _mock_db()
    execute_result = MagicMock()
    execute_result.scalar_one_or_none.return_value = None
    db.execute.return_value = execute_result

    result = await delete_product(uuid.uuid4(), tenant_id, db)
    assert result is False
```

- [ ] **Step 2: Jalankan test — pastikan FAIL**

```bash
cd /home/px/Projects/Reseller
pytest backend/tests/test_product_service.py -v
```

Expected: `ImportError` atau `ModuleNotFoundError` karena file belum ada.

- [ ] **Step 3: Buat schema**

```python
# backend/app/schemas/product.py
import uuid
from decimal import Decimal

from pydantic import BaseModel, Field, HttpUrl


class CreateProductRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    category: str | None = Field(None, max_length=100)
    base_price: Decimal | None = Field(None, gt=0)
    affiliate_link: str | None = None
    supplier_link: str | None = None
    margin_estimate: Decimal | None = Field(None, ge=0)


class UpdateProductRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = None
    category: str | None = Field(None, max_length=100)
    base_price: Decimal | None = Field(None, gt=0)
    affiliate_link: str | None = None
    supplier_link: str | None = None
    margin_estimate: Decimal | None = Field(None, ge=0)
    status: str | None = Field(None, pattern="^(active|inactive)$")


class ProductResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    description: str | None
    category: str | None
    base_price: Decimal | None
    affiliate_link: str | None
    supplier_link: str | None
    margin_estimate: Decimal | None
    status: str

    model_config = {"from_attributes": True}
```

- [ ] **Step 4: Buat service**

```python
# backend/app/services/product_service.py
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product
from app.schemas.product import CreateProductRequest, UpdateProductRequest

logger = logging.getLogger(__name__)


async def create_product(
    tenant_id: str, body: CreateProductRequest, db: AsyncSession
) -> Product:
    product = Product(
        tenant_id=uuid.UUID(tenant_id),
        name=body.name,
        description=body.description,
        category=body.category,
        base_price=body.base_price,
        affiliate_link=str(body.affiliate_link) if body.affiliate_link else None,
        supplier_link=str(body.supplier_link) if body.supplier_link else None,
        margin_estimate=body.margin_estimate,
        status="active",
    )
    db.add(product)
    await db.flush()
    logger.info("Product created", extra={"tenant_id": tenant_id, "product_id": str(product.id)})
    return product


async def list_products(tenant_id: str, db: AsyncSession) -> list[Product]:
    result = await db.execute(
        select(Product)
        .where(Product.tenant_id == uuid.UUID(tenant_id))
        .order_by(Product.created_at.desc())
    )
    return list(result.scalars().all())


async def update_product(
    product_id: uuid.UUID, tenant_id: str, body: UpdateProductRequest, db: AsyncSession
) -> Product | None:
    result = await db.execute(
        select(Product).where(
            Product.id == product_id,
            Product.tenant_id == uuid.UUID(tenant_id),
        )
    )
    product = result.scalar_one_or_none()
    if product is None:
        return None

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(product, field, value)

    logger.info("Product updated", extra={"product_id": str(product_id), "tenant_id": tenant_id})
    return product


async def delete_product(
    product_id: uuid.UUID, tenant_id: str, db: AsyncSession
) -> bool:
    result = await db.execute(
        select(Product).where(
            Product.id == product_id,
            Product.tenant_id == uuid.UUID(tenant_id),
        )
    )
    product = result.scalar_one_or_none()
    if product is None:
        return False

    await db.delete(product)
    logger.info("Product deleted", extra={"product_id": str(product_id), "tenant_id": tenant_id})
    return True
```

- [ ] **Step 5: Jalankan test — pastikan PASS**

```bash
pytest backend/tests/test_product_service.py -v
```

Expected: 4 test PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/schemas/product.py backend/app/services/product_service.py backend/tests/test_product_service.py
git commit -m "feat: product schema + service — CRUD per tenant"
```

---

## Task 2: Router — Product CRUD Endpoints

**Files:**
- Create: `backend/app/routers/products.py`
- Modify: `backend/app/main.py`

**Interfaces:**
- Consumes: `create_product`, `list_products`, `update_product`, `delete_product` dari Task 1; `ProductResponse` dari Task 1
- Produces:
  - `GET /api/v1/products` → `APIResponse[list[ProductResponse]]`
  - `POST /api/v1/products` → `APIResponse[ProductResponse]` (201)
  - `PATCH /api/v1/products/{product_id}` → `APIResponse[ProductResponse]`
  - `DELETE /api/v1/products/{product_id}` → `APIResponse[None]`

- [ ] **Step 1: Buat router**

```python
# backend/app/routers/products.py
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.schemas.base import APIResponse
from app.schemas.product import CreateProductRequest, ProductResponse, UpdateProductRequest
from app.services.product_service import (
    create_product,
    delete_product,
    list_products,
    update_product,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/products", tags=["products"])


@router.get("", response_model=APIResponse[list[ProductResponse]])
async def list_products_endpoint(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    tenant_id: str = request.state.tenant_id
    products = await list_products(tenant_id, db)
    return APIResponse(data=[ProductResponse.model_validate(p) for p in products])


@router.post("", response_model=APIResponse[ProductResponse], status_code=status.HTTP_201_CREATED)
async def create_product_endpoint(
    body: CreateProductRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    tenant_id: str = request.state.tenant_id
    async with db.begin():
        product = await create_product(tenant_id, body, db)
    return APIResponse(data=ProductResponse.model_validate(product), message="Produk berhasil ditambahkan.")


@router.patch("/{product_id}", response_model=APIResponse[ProductResponse])
async def update_product_endpoint(
    product_id: uuid.UUID,
    body: UpdateProductRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    tenant_id: str = request.state.tenant_id
    async with db.begin():
        product = await update_product(product_id, tenant_id, body, db)
    if product is None:
        raise HTTPException(status_code=404, detail="Produk tidak ditemukan.")
    return APIResponse(data=ProductResponse.model_validate(product))


@router.delete("/{product_id}", response_model=APIResponse[None])
async def delete_product_endpoint(
    product_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    tenant_id: str = request.state.tenant_id
    async with db.begin():
        deleted = await delete_product(product_id, tenant_id, db)
    if not deleted:
        raise HTTPException(status_code=404, detail="Produk tidak ditemukan.")
    return APIResponse(data=None, message="Produk berhasil dihapus.")
```

- [ ] **Step 2: Register router di main.py**

Buka `backend/app/main.py`. Tambahkan di bagian import dan `app.include_router`:

```python
# Tambah di import routers:
from app.routers import auth, conversations, features, leads, products, settings, webhooks

# Tambah setelah app.include_router(leads.router):
app.include_router(products.router)
```

- [ ] **Step 3: Test manual endpoint (pastikan server jalan)**

```bash
# Dari root project, jalankan dev server
cd backend && uvicorn app.main:app --reload --port 8000
```

Lalu test di Postman atau curl:
```bash
# Login dulu
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"your@email.com","password":"yourpassword"}' \
  -c /tmp/cookies.txt

# List products (harusnya kosong)
curl http://localhost:8000/api/v1/products -b /tmp/cookies.txt

# Tambah produk
curl -X POST http://localhost:8000/api/v1/products \
  -H "Content-Type: application/json" \
  -b /tmp/cookies.txt \
  -d '{"name":"Sepatu Lari","base_price":150000,"description":"Sepatu untuk lari marathon"}'
```

Expected: `{"success": true, "data": {...}, "message": "Produk berhasil ditambahkan."}`

- [ ] **Step 4: Commit**

```bash
git add backend/app/routers/products.py backend/app/main.py
git commit -m "feat: router /products — CRUD endpoint per tenant"
```

---

## Task 3: Schema & Service — Settings (Facebook Page Token)

**Files:**
- Create: `backend/app/schemas/settings.py`
- Create: `backend/app/services/settings_service.py`
- Create: `backend/app/routers/settings.py`
- Create: `backend/tests/test_settings_service.py`

**Interfaces:**
- Produces:
  - `save_fb_token(tenant_id: str, page_token: str, page_id: str, db: AsyncSession) -> TenantCredential`
  - `get_settings_status(tenant_id: str, db: AsyncSession) -> dict` — returns `{"facebook_connected": bool, "product_count": int}`
  - `GET /api/v1/settings` → `APIResponse[SettingsResponse]`
  - `POST /api/v1/settings/facebook-token` → `APIResponse[None]`

- [ ] **Step 1: Tulis test yang gagal**

```python
# backend/tests/test_settings_service.py
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.settings_service import get_settings_status, save_fb_token


def _mock_db():
    db = MagicMock()
    db.execute = AsyncMock()
    db.flush = AsyncMock()
    db.add = MagicMock()
    db.delete = AsyncMock()
    return db


@pytest.mark.asyncio
async def test_get_settings_status_no_credential():
    tenant_id = str(uuid.uuid4())
    db = _mock_db()

    # execute dipanggil 2x: sekali untuk credential, sekali untuk product count
    cred_result = MagicMock()
    cred_result.scalar_one_or_none.return_value = None

    count_result = MagicMock()
    count_result.scalar.return_value = 0

    db.execute.side_effect = [cred_result, count_result]

    status = await get_settings_status(tenant_id, db)
    assert status["facebook_connected"] is False
    assert status["product_count"] == 0


@pytest.mark.asyncio
async def test_get_settings_status_with_credential():
    tenant_id = str(uuid.uuid4())
    db = _mock_db()

    cred = MagicMock()
    cred.is_expired.return_value = False
    cred_result = MagicMock()
    cred_result.scalar_one_or_none.return_value = cred

    count_result = MagicMock()
    count_result.scalar.return_value = 3

    db.execute.side_effect = [cred_result, count_result]

    status = await get_settings_status(tenant_id, db)
    assert status["facebook_connected"] is True
    assert status["product_count"] == 3


@pytest.mark.asyncio
async def test_save_fb_token_creates_new():
    tenant_id = str(uuid.uuid4())
    db = _mock_db()

    existing_result = MagicMock()
    existing_result.scalar_one_or_none.return_value = None
    db.execute.return_value = existing_result

    with patch("app.services.settings_service.encrypt_credential", return_value="encrypted_token"):
        result = await save_fb_token(tenant_id, "raw_token_123", "page_id_456", db)

    db.add.assert_called_once()
    db.flush.assert_called_once()
```

- [ ] **Step 2: Jalankan test — pastikan FAIL**

```bash
pytest backend/tests/test_settings_service.py -v
```

Expected: `ImportError` karena file belum ada.

- [ ] **Step 3: Buat schema**

```python
# backend/app/schemas/settings.py
from pydantic import BaseModel, Field


class SaveFBTokenRequest(BaseModel):
    page_token: str = Field(..., min_length=10)
    page_id: str = Field(..., min_length=1)


class SettingsResponse(BaseModel):
    facebook_connected: bool
    product_count: int
```

- [ ] **Step 4: Buat service**

```python
# backend/app/services/settings_service.py
import logging
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import encrypt_credential
from app.models.product import Product
from app.models.tenant_credential import TenantCredential

logger = logging.getLogger(__name__)


async def get_settings_status(tenant_id: str, db: AsyncSession) -> dict:
    cred_result = await db.execute(
        select(TenantCredential).where(
            TenantCredential.tenant_id == uuid.UUID(tenant_id),
            TenantCredential.platform == "facebook",
        )
    )
    credential = cred_result.scalar_one_or_none()
    facebook_connected = credential is not None and not credential.is_expired()

    count_result = await db.execute(
        select(func.count()).where(
            Product.tenant_id == uuid.UUID(tenant_id),
            Product.status == "active",
        )
    )
    product_count = count_result.scalar() or 0

    return {"facebook_connected": facebook_connected, "product_count": product_count}


async def save_fb_token(
    tenant_id: str, page_token: str, page_id: str, db: AsyncSession
) -> TenantCredential:
    existing_result = await db.execute(
        select(TenantCredential).where(
            TenantCredential.tenant_id == uuid.UUID(tenant_id),
            TenantCredential.platform == "facebook",
        )
    )
    credential = existing_result.scalar_one_or_none()
    encrypted = encrypt_credential(page_token)

    if credential is None:
        credential = TenantCredential(
            tenant_id=uuid.UUID(tenant_id),
            platform="facebook",
            access_token_encrypted=encrypted,
        )
        db.add(credential)
    else:
        credential.access_token_encrypted = encrypted

    await db.flush()
    logger.info("FB token saved", extra={"tenant_id": tenant_id, "page_id": page_id})
    return credential
```

- [ ] **Step 5: Cek apakah `encrypt_credential` sudah ada di `security.py`**

```bash
grep -n "encrypt_credential\|decrypt_credential" backend/app/core/security.py
```

Jika belum ada `encrypt_credential`, tambahkan di `backend/app/core/security.py`:

```python
def encrypt_credential(plain_text: str) -> str:
    settings = get_settings()
    f = Fernet(settings.CREDENTIAL_ENCRYPTION_KEY.encode())
    return f.encrypt(plain_text.encode()).decode()
```

Jika `decrypt_credential` sudah ada tapi `encrypt_credential` belum — tambahkan saja fungsi itu.

- [ ] **Step 6: Jalankan test — pastikan PASS**

```bash
pytest backend/tests/test_settings_service.py -v
```

Expected: 3 test PASS.

- [ ] **Step 7: Buat router**

```python
# backend/app/routers/settings.py
import logging

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.schemas.base import APIResponse
from app.schemas.settings import SaveFBTokenRequest, SettingsResponse
from app.services.settings_service import get_settings_status, save_fb_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/settings", tags=["settings"])


@router.get("", response_model=APIResponse[SettingsResponse])
async def get_settings_endpoint(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    tenant_id: str = request.state.tenant_id
    status = await get_settings_status(tenant_id, db)
    return APIResponse(data=SettingsResponse(**status))


@router.post("/facebook-token", response_model=APIResponse[None])
async def save_facebook_token(
    body: SaveFBTokenRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    tenant_id: str = request.state.tenant_id
    async with db.begin():
        await save_fb_token(tenant_id, body.page_token, body.page_id, db)
    return APIResponse(data=None, message="Facebook Page token berhasil disimpan.")
```

- [ ] **Step 8: Register router di main.py**

```python
# backend/app/main.py — tambah di import dan include_router
from app.routers import auth, conversations, features, leads, products, settings, webhooks

app.include_router(settings.router)
```

- [ ] **Step 9: Commit**

```bash
git add backend/app/schemas/settings.py backend/app/services/settings_service.py \
        backend/app/routers/settings.py backend/app/main.py \
        backend/tests/test_settings_service.py
git commit -m "feat: settings service + router — status FB connection, save FB token"
```

---

## Task 4: Frontend — Products Page

**Files:**
- Create: `frontend/src/hooks/useProducts.ts`
- Create: `frontend/src/pages/Products.tsx`
- Modify: `frontend/src/App.tsx`

**Interfaces:**
- Consumes: `GET /api/v1/products`, `POST /api/v1/products`, `PATCH /api/v1/products/{id}`, `DELETE /api/v1/products/{id}`
- Produces: halaman `/products` (protected route), `useProducts()` hook

- [ ] **Step 1: Buat hook**

```typescript
// frontend/src/hooks/useProducts.ts
import { useCallback, useEffect, useState } from "react";
import api from "@/lib/api";

export interface ProductResponse {
  id: string;
  name: string;
  description: string | null;
  category: string | null;
  base_price: string | null;
  affiliate_link: string | null;
  status: string;
}

export interface CreateProductPayload {
  name: string;
  description?: string;
  category?: string;
  base_price?: number;
  affiliate_link?: string;
}

export function useProducts() {
  const [products, setProducts] = useState<ProductResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchProducts = useCallback(async () => {
    setIsLoading(true);
    try {
      const res = await api.get<{ data: ProductResponse[] }>("/products");
      setProducts(res.data.data ?? []);
    } catch {
      setError("Gagal memuat produk.");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => { fetchProducts(); }, [fetchProducts]);

  async function addProduct(payload: CreateProductPayload): Promise<ProductResponse> {
    const res = await api.post<{ data: ProductResponse }>("/products", payload);
    await fetchProducts();
    return res.data.data;
  }

  async function updateProduct(id: string, payload: Partial<CreateProductPayload & { status: string }>): Promise<void> {
    await api.patch(`/products/${id}`, payload);
    await fetchProducts();
  }

  async function deleteProduct(id: string): Promise<void> {
    await api.delete(`/products/${id}`);
    setProducts((prev) => prev.filter((p) => p.id !== id));
  }

  return { products, isLoading, error, addProduct, updateProduct, deleteProduct };
}
```

- [ ] **Step 2: Buat halaman Products**

```tsx
// frontend/src/pages/Products.tsx
import { useState } from "react";
import { useProducts, type CreateProductPayload } from "@/hooks/useProducts";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

function formatPrice(price: string | null) {
  if (!price) return "—";
  return `Rp ${parseInt(price).toLocaleString("id-ID")}`;
}

export default function Products() {
  const { products, isLoading, error, addProduct, deleteProduct } = useProducts();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<CreateProductPayload>({ name: "" });
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.name.trim()) { setFormError("Nama produk wajib diisi."); return; }
    setSubmitting(true);
    setFormError(null);
    try {
      await addProduct(form);
      setForm({ name: "" });
      setShowForm(false);
    } catch {
      setFormError("Gagal menambahkan produk. Coba lagi.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="min-h-screen bg-slate-50 p-6">
      <div className="mx-auto max-w-3xl">
        <div className="mb-6 flex items-center justify-between">
          <h1 className="text-xl font-semibold text-slate-900">Produk</h1>
          <Button onClick={() => setShowForm((v) => !v)} size="sm">
            {showForm ? "Batal" : "+ Tambah Produk"}
          </Button>
        </div>

        {showForm && (
          <form onSubmit={handleSubmit} className="mb-6 rounded-lg border bg-white p-4 shadow-sm space-y-3">
            <div>
              <Label htmlFor="name">Nama Produk *</Label>
              <Input id="name" value={form.name} onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))} placeholder="Sepatu Lari Pro" />
            </div>
            <div>
              <Label htmlFor="desc">Deskripsi</Label>
              <Input id="desc" value={form.description ?? ""} onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))} placeholder="Cocok untuk lari marathon..." />
            </div>
            <div className="flex gap-3">
              <div className="flex-1">
                <Label htmlFor="price">Harga (Rp)</Label>
                <Input id="price" type="number" min={0} value={form.base_price ?? ""} onChange={(e) => setForm((f) => ({ ...f, base_price: e.target.value ? Number(e.target.value) : undefined }))} placeholder="150000" />
              </div>
              <div className="flex-1">
                <Label htmlFor="link">Link Affiliate</Label>
                <Input id="link" value={form.affiliate_link ?? ""} onChange={(e) => setForm((f) => ({ ...f, affiliate_link: e.target.value }))} placeholder="https://..." />
              </div>
            </div>
            {formError && <p className="text-sm text-red-600">{formError}</p>}
            <Button type="submit" disabled={submitting} size="sm">
              {submitting ? "Menyimpan..." : "Simpan Produk"}
            </Button>
          </form>
        )}

        {isLoading && <p className="text-sm text-slate-500">Memuat produk...</p>}
        {error && <p className="text-sm text-red-500">{error}</p>}

        {!isLoading && products.length === 0 && (
          <div className="rounded-lg border bg-white p-8 text-center text-sm text-slate-500">
            Belum ada produk. Tambahkan produk agar AI bisa menjawab pertanyaan customer.
          </div>
        )}

        <div className="space-y-3">
          {products.map((p) => (
            <div key={p.id} className="flex items-start justify-between gap-3 rounded-lg border bg-white p-4 shadow-sm">
              <div className="min-w-0">
                <p className="font-medium text-slate-900 truncate">{p.name}</p>
                {p.description && <p className="text-sm text-slate-500 mt-0.5 truncate">{p.description}</p>}
                <div className="mt-1 flex gap-3 text-xs text-slate-400">
                  <span>{formatPrice(p.base_price)}</span>
                  {p.affiliate_link && <span className="truncate max-w-[200px]">{p.affiliate_link}</span>}
                </div>
              </div>
              <Button
                variant="ghost"
                size="sm"
                className="text-red-500 hover:text-red-700 shrink-0"
                onClick={() => deleteProduct(p.id)}
              >
                Hapus
              </Button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Tambah route di App.tsx**

```tsx
// frontend/src/App.tsx — tambah import dan route
import Products from "@/pages/Products";

// Tambah setelah route /leads:
<Route
  path="/products"
  element={
    <ProtectedRoute>
      <Products />
    </ProtectedRoute>
  }
/>
```

- [ ] **Step 4: Test di browser**

```bash
cd frontend && npm run dev
```

Buka `http://localhost:5173/products`. Pastikan:
- List kosong tampil pesan "Belum ada produk"
- Form tambah produk bisa dibuka dan disubmit
- Produk baru muncul di list setelah disimpan
- Tombol Hapus menghapus produk

- [ ] **Step 5: Commit**

```bash
git add frontend/src/hooks/useProducts.ts frontend/src/pages/Products.tsx frontend/src/App.tsx
git commit -m "feat: Products page — list, tambah, hapus produk"
```

---

## Task 5: Frontend — Settings Page (Connect Facebook)

**Files:**
- Create: `frontend/src/hooks/useSettings.ts`
- Create: `frontend/src/pages/Settings.tsx`
- Modify: `frontend/src/App.tsx`

**Interfaces:**
- Consumes: `GET /api/v1/settings`, `POST /api/v1/settings/facebook-token`
- Produces: halaman `/settings` (protected route)

- [ ] **Step 1: Buat hook**

```typescript
// frontend/src/hooks/useSettings.ts
import { useCallback, useEffect, useState } from "react";
import api from "@/lib/api";

export interface SettingsStatus {
  facebook_connected: boolean;
  product_count: number;
}

export function useSettings() {
  const [status, setStatus] = useState<SettingsStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const fetchStatus = useCallback(async () => {
    setIsLoading(true);
    try {
      const res = await api.get<{ data: SettingsStatus }>("/settings");
      setStatus(res.data.data);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => { fetchStatus(); }, [fetchStatus]);

  async function saveFBToken(pageToken: string, pageId: string): Promise<void> {
    await api.post("/settings/facebook-token", { page_token: pageToken, page_id: pageId });
    await fetchStatus();
  }

  return { status, isLoading, saveFBToken };
}
```

- [ ] **Step 2: Buat halaman Settings**

```tsx
// frontend/src/pages/Settings.tsx
import { useState } from "react";
import { useSettings } from "@/hooks/useSettings";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export default function Settings() {
  const { status, isLoading, saveFBToken } = useSettings();
  const [pageToken, setPageToken] = useState("");
  const [pageId, setPageId] = useState("");
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saveSuccess, setSaveSuccess] = useState(false);

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    if (!pageToken.trim() || !pageId.trim()) {
      setSaveError("Page Token dan Page ID wajib diisi.");
      return;
    }
    setSaving(true);
    setSaveError(null);
    setSaveSuccess(false);
    try {
      await saveFBToken(pageToken.trim(), pageId.trim());
      setPageToken("");
      setPageId("");
      setSaveSuccess(true);
    } catch {
      setSaveError("Gagal menyimpan token. Pastikan token valid.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="min-h-screen bg-slate-50 p-6">
      <div className="mx-auto max-w-xl">
        <h1 className="mb-6 text-xl font-semibold text-slate-900">Pengaturan</h1>

        <div className="rounded-lg border bg-white p-5 shadow-sm">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="font-medium text-slate-800">Facebook Page</h2>
            {!isLoading && (
              <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${status?.facebook_connected ? "bg-green-100 text-green-700" : "bg-slate-100 text-slate-500"}`}>
                {status?.facebook_connected ? "Terhubung" : "Belum terhubung"}
              </span>
            )}
          </div>

          <p className="mb-4 text-sm text-slate-500">
            Masukkan Facebook Page Access Token untuk mengaktifkan auto-reply komentar dan Messenger DM.
            Generate token di{" "}
            <a href="https://developers.facebook.com/tools/explorer" target="_blank" rel="noreferrer" className="text-blue-600 hover:underline">
              Graph API Explorer
            </a>{" "}
            dengan permission <code className="rounded bg-slate-100 px-1 text-xs">pages_manage_engagement</code>.
          </p>

          <form onSubmit={handleSave} className="space-y-3">
            <div>
              <Label htmlFor="pageId">Page ID</Label>
              <Input id="pageId" value={pageId} onChange={(e) => setPageId(e.target.value)} placeholder="1234567890" />
            </div>
            <div>
              <Label htmlFor="pageToken">Page Access Token</Label>
              <Input id="pageToken" type="password" value={pageToken} onChange={(e) => setPageToken(e.target.value)} placeholder="EAAxxxx..." />
            </div>
            {saveError && <p className="text-sm text-red-600">{saveError}</p>}
            {saveSuccess && <p className="text-sm text-green-600">Token berhasil disimpan. AI aktif.</p>}
            <Button type="submit" disabled={saving} size="sm">
              {saving ? "Menyimpan..." : "Simpan Token"}
            </Button>
          </form>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Tambah route di App.tsx**

```tsx
// frontend/src/App.tsx — tambah import dan route
import Settings from "@/pages/Settings";

// Tambah setelah route /products:
<Route
  path="/settings"
  element={
    <ProtectedRoute>
      <Settings />
    </ProtectedRoute>
  }
/>
```

- [ ] **Step 4: Test di browser**

Buka `http://localhost:5173/settings`. Pastikan:
- Status "Belum terhubung" tampil kalau belum ada token
- Form bisa disubmit dengan Page ID dan Page Token
- Setelah submit, badge berubah jadi "Terhubung"
- Error message tampil kalau field kosong

- [ ] **Step 5: Commit**

```bash
git add frontend/src/hooks/useSettings.ts frontend/src/pages/Settings.tsx frontend/src/App.tsx
git commit -m "feat: Settings page — connect Facebook Page via UI"
```

---

## Self-Review

### Spec Coverage

| Requirement | Task |
|-------------|------|
| Product management CRUD `/products` | Task 1 + 2 |
| Settings page: connect FB via UI | Task 3 + 5 |
| Token FB dienkripsi sebelum disimpan | Task 3 (`encrypt_credential`) |
| Multi-tenant isolation semua query | Task 1, 3 (filter `tenant_id`) |
| Response format `APIResponse[T]` | Task 2, 3 |
| Validasi input Pydantic | Task 1 (`CreateProductRequest`, `UpdateProductRequest`) |
| Frontend protected route | Task 4, 5 |

### Placeholder Scan — Bersih ✓

### Type Consistency

- `create_product(tenant_id: str, body: CreateProductRequest, db: AsyncSession) -> Product` — konsisten antara Task 1 dan Task 2
- `save_fb_token(tenant_id: str, page_token: str, page_id: str, db: AsyncSession) -> TenantCredential` — konsisten antara Task 3 service dan router
- `ProductResponse.model_validate(p)` — konsisten, `model_config = {"from_attributes": True}` sudah ada di schema

### Gap Check

- `encrypt_credential` mungkin belum ada di `security.py` — Task 3 Step 5 sudah handle dengan instruksi cek dan tambah jika belum ada.
- Onboarding wizard (flow terarah setelah register) tidak diimplementasikan di plan ini — scope dipersempit ke CRUD + Settings. Wizard bisa ditambah sebagai Fase 4a extension setelah 4b/4c selesai.
