# Lead Intelligence Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tambahkan klasifikasi lead otomatis (hot/warm/cold) dari percakapan Facebook/Messenger yang sudah ada, dengan Leads dashboard untuk reseller follow up manual.

**Architecture:** Rule-based tier classification (zero LLM call tambahan) dari intent+sentiment yang sudah tersimpan di tabel `conversations`. Lead worker di-chain setelah engagement worker selesai commit. Auto-decay harian via Celery Beat.

**Tech Stack:** FastAPI, SQLAlchemy 2.0 async, Alembic, Celery 5 + Celery Beat, React 18 + Vite + Tailwind CSS + shadcn/ui, Zustand, Axios.

## Global Constraints

- RULE-01: Setiap fungsi yang menyentuh integrasi eksternal wajib panggil `check_feature_status()` dulu
- RULE-02: Tidak ada raw error ke user — semua exception ditangkap sebelum response
- RULE-03: Setiap query DB wajib sertakan filter `tenant_id`
- RULE-04: Setiap Celery task wajib retry & log ke `system_logs`
- RULE-06: Semua input wajib Pydantic v2 schema
- RULE-07: FeatureGate wajib di setiap fitur UI yang bergantung integrasi eksternal
- RULE-08: Tidak ada `print()` di production — pakai `logging`
- RULE-09: Perubahan schema DB wajib via Alembic migration
- RULE-10: Semua fungsi publik wajib type hint
- Backend root: `backend/` (semua path Python relatif ke sini)
- Frontend root: `frontend/src/` (semua path TS relatif ke sini)
- Tier values: `'hot'` | `'warm'` | `'cold'` (lowercase, varchar 10)
- Status values: `'active'` | `'archived'` | `'resolved'` (lowercase, varchar 20)
- API prefix: `/api/v1/leads`
- Tests dijalankan dari `backend/`: `pytest tests/ -v`
- Feature flag name: `"lead_classification"`

---

## File Map

**Baru (backend):**
- `app/models/lead.py` — SQLAlchemy Lead model
- `app/schemas/lead.py` — Pydantic LeadResponse + LeadCustomerInfo
- `app/services/lead_service.py` — `_calculate_tier`, `upsert_lead`, `archive_lead`, `resolve_lead`, `run_decay`
- `app/routers/leads.py` — GET /leads, PATCH /archive, PATCH /resolve
- `workers/lead_worker.py` — `classify_lead` task + `decay_leads` task
- `tests/test_lead_service.py` — unit tests untuk `_calculate_tier` + service functions

**Dimodifikasi (backend):**
- `app/models/__init__.py` — import Lead
- `app/services/engagement_service.py` — `process_facebook_comment` dan `process_messenger_message` return `str` (customer_id)
- `workers/engagement_worker.py` — chain `classify_lead.delay()` setelah commit
- `workers/celery_app.py` — tambah `lead_worker` ke include + beat_schedule + task_routes
- `app/core/feature_flags.py` — tambah `lead_classification` ke plan `pro` dan `enterprise`
- `app/main.py` — register leads router
- `alembic/versions/` — migration baru

**Baru (frontend):**
- `src/hooks/useLeads.ts` — polling hook + archive/resolve actions
- `src/pages/Leads.tsx` — halaman Leads dengan tabel + filter + aksi

**Dimodifikasi (frontend):**
- `src/App.tsx` — tambah route `/leads` + nav link

---

## Task 1: Lead Model + Alembic Migration

**Files:**
- Create: `app/models/lead.py`
- Modify: `app/models/__init__.py`
- Create: `alembic/versions/<hash>_add_leads_table.py` (di-generate oleh Alembic)

**Interfaces:**
- Produces: `Lead` class dengan atribut `id`, `tenant_id`, `customer_id`, `tier`, `tier_reason`, `interaction_count`, `last_interaction`, `status`, `resolved_at` — dipakai Task 3 (lead_service) dan Task 5 (router)

- [ ] **Step 1: Buat `app/models/lead.py`**

```python
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Lead(Base, TimestampMixin):
    __tablename__ = "leads"
    __table_args__ = (
        UniqueConstraint("tenant_id", "customer_id", name="uq_leads_tenant_customer"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tier: Mapped[str] = mapped_column(String(10), nullable=False)
    tier_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    interaction_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_interaction: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
```

- [ ] **Step 2: Tambah import Lead ke `app/models/__init__.py`**

Buka `app/models/__init__.py`. Tambahkan:

```python
from app.models.lead import Lead  # noqa: F401
```

- [ ] **Step 3: Generate Alembic migration**

Jalankan dari direktori `backend/`:

```bash
alembic revision --autogenerate -m "add_leads_table"
```

Buka file migration yang baru dibuat di `alembic/versions/`. Pastikan `upgrade()` berisi:
- `create_table('leads', ...)` dengan semua kolom
- `create_index` untuk `(tenant_id, status, tier)` — composite
- `create_index` untuk `(tenant_id, last_interaction)`
- `UniqueConstraint` pada `(tenant_id, customer_id)`

Jika index composite tidak di-generate otomatis, tambahkan manual:

```python
op.create_index("ix_leads_tenant_status_tier", "leads", ["tenant_id", "status", "tier"])
op.create_index("ix_leads_tenant_last_interaction", "leads", ["tenant_id", "last_interaction"])
```

- [ ] **Step 4: Jalankan migration**

```bash
alembic upgrade head
```

Expected output: `Running upgrade <prev> -> <new>, add_leads_table`

- [ ] **Step 5: Verifikasi tabel di DB**

```bash
python -c "
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import get_settings
async def check():
    engine = create_async_engine(get_settings().DATABASE_URL)
    async with engine.connect() as conn:
        result = await conn.execute(__import__('sqlalchemy').text(\"SELECT column_name FROM information_schema.columns WHERE table_name='leads' ORDER BY ordinal_position\"))
        for row in result: print(row[0])
    await engine.dispose()
asyncio.run(check())
"
```

Expected: id, tenant_id, customer_id, tier, tier_reason, interaction_count, last_interaction, status, resolved_at, created_at, updated_at

- [ ] **Step 6: Commit**

```bash
git add app/models/lead.py app/models/__init__.py alembic/versions/
git commit -m "feat: Lead model + Alembic migration add_leads_table"
```

---

## Task 2: Lead Service — `_calculate_tier` + Tests

**Files:**
- Create: `app/services/lead_service.py` (hanya `_calculate_tier` dulu)
- Create: `tests/test_lead_service.py`

**Interfaces:**
- Produces: `_calculate_tier(conversations: list) -> tuple[str, str]` — input list object dengan attr `intent: str | None` dan `sentiment: str | None`. Return `(tier, tier_reason)`.
- Dipakai Task 3 (`upsert_lead`)

- [ ] **Step 1: Tulis failing tests**

Buat `tests/test_lead_service.py`:

```python
import pytest
from unittest.mock import MagicMock

from app.services.lead_service import _calculate_tier


def _conv(intent: str, sentiment: str = "neutral") -> MagicMock:
    c = MagicMock()
    c.intent = intent
    c.sentiment = sentiment
    return c


def test_calculate_tier_hot():
    convs = [_conv("niat_beli", "positive")]
    tier, reason = _calculate_tier(convs)
    assert tier == "hot"
    assert reason == "niat_beli:positive"


def test_calculate_tier_hot_beats_warm():
    # Kalau ada niat_beli:positive, tier hot meskipun ada tanya_info lain
    convs = [_conv("tanya_info"), _conv("tanya_info"), _conv("niat_beli", "positive")]
    tier, reason = _calculate_tier(convs)
    assert tier == "hot"


def test_calculate_tier_warm_niat_beli_neutral():
    convs = [_conv("niat_beli", "neutral")]
    tier, reason = _calculate_tier(convs)
    assert tier == "warm"
    assert reason == "niat_beli:neutral"


def test_calculate_tier_warm_niat_beli_negative():
    convs = [_conv("niat_beli", "negative")]
    tier, reason = _calculate_tier(convs)
    assert tier == "warm"


def test_calculate_tier_warm_repeat_tanya_info():
    convs = [_conv("tanya_info"), _conv("tanya_info")]
    tier, reason = _calculate_tier(convs)
    assert tier == "warm"
    assert reason == "tanya_info:2x"


def test_calculate_tier_cold_spam_only():
    convs = [_conv("spam"), _conv("spam")]
    tier, reason = _calculate_tier(convs)
    assert tier == "cold"
    assert reason == "spam_only"


def test_calculate_tier_cold_single_tanya_info():
    convs = [_conv("tanya_info")]
    tier, reason = _calculate_tier(convs)
    assert tier == "cold"
    assert reason == "single_interaction"


def test_calculate_tier_cold_empty():
    tier, reason = _calculate_tier([])
    assert tier == "cold"
    assert reason == "no_interactions"


def test_calculate_tier_ignores_none_intent():
    # Conversation dengan intent=None tidak boleh crash
    convs = [_conv(None, None), _conv("tanya_info")]  # type: ignore
    tier, reason = _calculate_tier(convs)
    assert tier == "cold"  # hanya 1 valid tanya_info
```

- [ ] **Step 2: Jalankan — pastikan gagal**

```bash
pytest tests/test_lead_service.py -v
```

Expected: `ModuleNotFoundError: No module named 'app.services.lead_service'`

- [ ] **Step 3: Buat `app/services/lead_service.py` dengan `_calculate_tier`**

```python
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation
from app.models.customer import Customer
from app.models.lead import Lead
from app.models.system_log import SystemLog

logger = logging.getLogger(__name__)


def _calculate_tier(conversations: list) -> tuple[str, str]:
    """
    Pure function — hitung tier lead dari list conversations.
    Input: list object dengan attr .intent (str|None) dan .sentiment (str|None).
    Return: (tier, tier_reason)
    """
    if not conversations:
        return "cold", "no_interactions"

    valid = [c for c in conversations if c.intent is not None]

    # HOT: ada niat_beli + positive
    for c in valid:
        if c.intent == "niat_beli" and c.sentiment == "positive":
            return "hot", "niat_beli:positive"

    # WARM: niat_beli (sentiment apapun)
    for c in valid:
        if c.intent == "niat_beli":
            return "warm", f"niat_beli:{c.sentiment or 'unknown'}"

    # WARM: tanya_info >= 2x
    tanya_count = sum(1 for c in valid if c.intent == "tanya_info")
    if tanya_count >= 2:
        return "warm", f"tanya_info:{tanya_count}x"

    # COLD: semua spam
    non_spam = [c for c in valid if c.intent != "spam"]
    if not non_spam:
        return "cold", "spam_only"

    # COLD: single interaction
    return "cold", "single_interaction"
```

- [ ] **Step 4: Jalankan — pastikan lulus**

```bash
pytest tests/test_lead_service.py -v
```

Expected: 9 tests PASSED

- [ ] **Step 5: Commit**

```bash
git add app/services/lead_service.py tests/test_lead_service.py
git commit -m "feat: lead_service._calculate_tier + tests"
```

---

## Task 3: Lead Service — `upsert_lead`, `archive_lead`, `resolve_lead`, `run_decay`

**Files:**
- Modify: `app/services/lead_service.py` — tambah 4 fungsi async

**Interfaces:**
- Consumes: `Lead` (Task 1), `_calculate_tier` (Task 2), `Conversation`, `Customer` models
- Produces:
  - `upsert_lead(tenant_id: str, customer_id: str, db: AsyncSession) -> Lead`
  - `archive_lead(lead_id: uuid.UUID, tenant_id: str, db: AsyncSession) -> Lead`
  - `resolve_lead(lead_id: uuid.UUID, tenant_id: str, db: AsyncSession) -> Lead`
  - `run_decay(db: AsyncSession) -> int`
- Dipakai Task 4 (lead_worker) dan Task 5 (router)

- [ ] **Step 1: Tulis failing tests untuk `upsert_lead`**

Tambahkan ke `tests/test_lead_service.py`:

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
from datetime import datetime, timezone


@pytest.mark.asyncio
async def test_upsert_lead_creates_new():
    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()

    tenant_id = str(uuid.uuid4())
    customer_id = str(uuid.uuid4())

    conv = _conv("niat_beli", "positive")
    conv.created_at = datetime.now(timezone.utc)

    with patch("app.services.lead_service._fetch_conversations", return_value=[conv]), \
         patch("app.services.lead_service._fetch_lead", return_value=None):
        from app.services.lead_service import upsert_lead
        result = await upsert_lead(tenant_id, customer_id, db)

    db.add.assert_called_once()
    added: Lead = db.add.call_args[0][0]
    assert added.tier == "hot"
    assert added.tier_reason == "niat_beli:positive"
    assert added.interaction_count == 1


@pytest.mark.asyncio
async def test_upsert_lead_updates_existing():
    db = AsyncMock()
    db.add = MagicMock()

    tenant_id = str(uuid.uuid4())
    customer_id = str(uuid.uuid4())

    conv = _conv("niat_beli", "positive")
    conv.created_at = datetime.now(timezone.utc)

    existing = MagicMock(spec=Lead)
    existing.tier = "cold"

    with patch("app.services.lead_service._fetch_conversations", return_value=[conv]), \
         patch("app.services.lead_service._fetch_lead", return_value=existing):
        from app.services.lead_service import upsert_lead
        result = await upsert_lead(tenant_id, customer_id, db)

    assert existing.tier == "hot"
    assert existing.interaction_count == 1
    db.add.assert_not_called()  # update in-place, bukan add baru
```

- [ ] **Step 2: Jalankan — pastikan gagal**

```bash
pytest tests/test_lead_service.py::test_upsert_lead_creates_new tests/test_lead_service.py::test_upsert_lead_updates_existing -v
```

Expected: ImportError atau AttributeError

- [ ] **Step 3: Tambahkan fungsi-fungsi async ke `app/services/lead_service.py`**

Tambahkan setelah `_calculate_tier`:

```python
async def _fetch_conversations(
    tenant_id: str, customer_id: str, db: AsyncSession
) -> list[Conversation]:
    result = await db.execute(
        select(Conversation).where(
            Conversation.tenant_id == uuid.UUID(tenant_id),
            Conversation.customer_id == uuid.UUID(customer_id),
        )
    )
    return list(result.scalars().all())


async def _fetch_lead(
    tenant_id: str, customer_id: str, db: AsyncSession
) -> Lead | None:
    result = await db.execute(
        select(Lead).where(
            Lead.tenant_id == uuid.UUID(tenant_id),
            Lead.customer_id == uuid.UUID(customer_id),
        )
    )
    return result.scalar_one_or_none()


async def upsert_lead(
    tenant_id: str, customer_id: str, db: AsyncSession
) -> Lead:
    conversations = await _fetch_conversations(tenant_id, customer_id, db)
    tier, tier_reason = _calculate_tier(conversations)

    last_interaction = None
    if conversations:
        last_interaction = max(c.created_at for c in conversations if c.created_at)

    interaction_count = len(conversations)
    existing = await _fetch_lead(tenant_id, customer_id, db)

    if existing is None:
        lead = Lead(
            tenant_id=uuid.UUID(tenant_id),
            customer_id=uuid.UUID(customer_id),
            tier=tier,
            tier_reason=tier_reason,
            interaction_count=interaction_count,
            last_interaction=last_interaction,
            status="active",
        )
        db.add(lead)
        logger.info(
            "Lead created",
            extra={"tenant_id": tenant_id, "customer_id": customer_id, "tier": tier},
        )
        return lead

    existing.tier = tier
    existing.tier_reason = tier_reason
    existing.interaction_count = interaction_count
    existing.last_interaction = last_interaction
    logger.info(
        "Lead updated",
        extra={"tenant_id": tenant_id, "customer_id": customer_id, "tier": tier},
    )
    return existing


async def archive_lead(
    lead_id: uuid.UUID, tenant_id: str, db: AsyncSession
) -> Lead | None:
    result = await db.execute(
        select(Lead).where(
            Lead.id == lead_id,
            Lead.tenant_id == uuid.UUID(tenant_id),  # RULE-03
        )
    )
    lead = result.scalar_one_or_none()
    if lead is None:
        return None
    lead.status = "archived"
    logger.info("Lead archived", extra={"lead_id": str(lead_id), "tenant_id": tenant_id})
    return lead


async def resolve_lead(
    lead_id: uuid.UUID, tenant_id: str, db: AsyncSession
) -> Lead | None:
    result = await db.execute(
        select(Lead).where(
            Lead.id == lead_id,
            Lead.tenant_id == uuid.UUID(tenant_id),  # RULE-03
        )
    )
    lead = result.scalar_one_or_none()
    if lead is None:
        return None
    lead.status = "resolved"
    lead.resolved_at = datetime.now(timezone.utc)
    logger.info("Lead resolved", extra={"lead_id": str(lead_id), "tenant_id": tenant_id})
    return lead


async def run_decay(db: AsyncSession) -> int:
    """
    Auto-decay tiers berdasarkan last_interaction.
    Return jumlah lead yang di-update.
    """
    from datetime import timedelta
    from sqlalchemy import and_, or_

    now = datetime.now(timezone.utc)
    count = 0

    # hot → warm: tidak aktif > 1 hari
    result = await db.execute(
        select(Lead).where(
            Lead.tier == "hot",
            Lead.status == "active",
            Lead.last_interaction < now - timedelta(days=1),
        )
    )
    for lead in result.scalars().all():
        lead.tier = "warm"
        lead.tier_reason = "decayed:hot_to_warm"
        count += 1

    # warm → cold: tidak aktif > 2 hari
    result = await db.execute(
        select(Lead).where(
            Lead.tier == "warm",
            Lead.status == "active",
            Lead.last_interaction < now - timedelta(days=2),
        )
    )
    for lead in result.scalars().all():
        lead.tier = "cold"
        lead.tier_reason = "decayed:warm_to_cold"
        count += 1

    # cold → archived: tidak aktif > 7 hari
    result = await db.execute(
        select(Lead).where(
            Lead.tier == "cold",
            Lead.status == "active",
            Lead.last_interaction < now - timedelta(days=7),
        )
    )
    for lead in result.scalars().all():
        lead.status = "archived"
        count += 1

    logger.info("Lead decay completed", extra={"updated_count": count})
    return count
```

- [ ] **Step 4: Tambah test decay ke `tests/test_lead_service.py`**

```python
@pytest.mark.asyncio
async def test_run_decay_hot_to_warm():
    from datetime import timedelta
    from app.services.lead_service import run_decay

    db = AsyncMock()
    now = datetime.now(timezone.utc)

    hot_lead = MagicMock(spec=Lead)
    hot_lead.tier = "hot"
    hot_lead.status = "active"
    hot_lead.last_interaction = now - timedelta(days=2)

    # Simulasi: scalars().all() return list yang berbeda per panggilan
    call_count = 0
    async def mock_execute(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        result = MagicMock()
        if call_count == 1:
            result.scalars.return_value.all.return_value = [hot_lead]
        else:
            result.scalars.return_value.all.return_value = []
        return result

    db.execute = mock_execute
    count = await run_decay(db)
    assert hot_lead.tier == "warm"
    assert count >= 1
```

- [ ] **Step 5: Jalankan semua tests**

```bash
pytest tests/test_lead_service.py -v
```

Expected: semua tests PASSED

- [ ] **Step 6: Commit**

```bash
git add app/services/lead_service.py tests/test_lead_service.py
git commit -m "feat: lead_service upsert_lead, archive_lead, resolve_lead, run_decay"
```

---

## Task 4: Lead Worker (Celery) + Engagement Worker Chain

**Files:**
- Create: `workers/lead_worker.py`
- Modify: `workers/celery_app.py`
- Modify: `workers/engagement_worker.py`
- Modify: `app/services/engagement_service.py`

**Interfaces:**
- Consumes: `upsert_lead`, `run_decay` (Task 3)
- Consumes: `check_feature_status` (existing `app/core/feature_flags.py`)
- Produces:
  - `classify_lead(tenant_id: str, customer_id: str) -> None` — Celery task, queue `"engagement"`
  - `decay_leads() -> None` — Celery task, queue `"engagement"`
- `process_facebook_comment` dan `process_messenger_message` sekarang return `str | None` (customer_id UUID string)

- [ ] **Step 1: Update `app/core/feature_flags.py` — tambah `lead_classification`**

Buka `app/core/feature_flags.py`. Update `PLAN_FEATURES`:

```python
PLAN_FEATURES: dict[str, list[str]] = {
    "free": ["instagram_reply"],
    "starter": ["instagram_reply", "tiktok_reply"],
    "pro": [
        "instagram_reply",
        "tiktok_reply",
        "facebook_reply",
        "whatsapp_reply",
        "lead_classification",
        "analytics",
    ],
    "enterprise": ["*"],
}
```

Tambahkan `"lead_classification"` juga ke `CREDENTIAL_FREE_FEATURES`:

```python
CREDENTIAL_FREE_FEATURES = {"analytics", "product_discovery", "lead_classification"}
```

- [ ] **Step 2: Update `app/services/engagement_service.py` — return customer_id**

`process_facebook_comment` dan `process_messenger_message` harus return `str | None` (customer_id sebagai string UUID). Ini dibutuhkan supaya engagement worker bisa chain ke lead worker setelah commit.

Ubah signature dan return statement di kedua fungsi:

```python
async def process_facebook_comment(
    tenant_id: str, event: dict, db: AsyncSession
) -> str | None:
    # ... (semua kode existing sama persis)
    # Di baris terakhir sebelum return (atau di setiap return path), kembalikan customer_id:

    # Ganti semua `return` menjadi:
    # return str(customer.id)    ← saat berhasil buat/ambil customer
    # return None                ← saat early return (no credential, dedup, dll)
```

Perubahan konkret — di `process_facebook_comment`, temukan setiap return point:

```python
# Early returns yang tidak punya customer — return None
# Return setelah customer dibuat — return str(customer.id)
```

Contoh posisi return yang perlu diubah:
1. Setelah `await log_skip(...)` → `return None`
2. Setelah `if tenant is None` → `return None`
3. Setelah credential check `return None`
4. Setelah dedup `existing is not None` → `return None`
5. Setelah eskalasi `db.add(conv)` → `return str(customer.id)`
6. Di akhir setelah `db.add(conv)` normal → `return str(customer.id)`

Lakukan hal yang sama untuk `process_messenger_message`.

- [ ] **Step 3: Buat `workers/lead_worker.py`**

```python
import asyncio
import logging

from workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="workers.lead_worker.classify_lead",
    queue="engagement",
    max_retries=3,
    default_retry_delay=30,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def classify_lead(self, tenant_id: str, customer_id: str) -> None:
    """Klasifikasi lead untuk satu customer setelah conversation baru masuk."""

    async def _run() -> None:
        from sqlalchemy.pool import NullPool
        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
        from app.core.config import get_settings
        from app.core.feature_flags import FeatureStatus, check_feature_status, log_skip
        from app.services.lead_service import upsert_lead

        import app.models.user  # noqa: F401

        _settings = get_settings()
        _engine = create_async_engine(_settings.DATABASE_URL, poolclass=NullPool)
        _Session = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)

        try:
            async with _Session() as session:
                # RULE-01: cek feature flag
                status = await check_feature_status(tenant_id, "lead_classification", session)
                if status != FeatureStatus.ACTIVE:
                    await log_skip(tenant_id, "lead_classification", status)
                    return

                async with session.begin():
                    await upsert_lead(tenant_id, customer_id, session)
        finally:
            await _engine.dispose()

    try:
        asyncio.run(_run())
        logger.info(
            "Lead classified",
            extra={"tenant_id": tenant_id, "customer_id": customer_id},
        )
    except Exception as exc:
        logger.error(
            "classify_lead failed",
            extra={"tenant_id": tenant_id, "customer_id": customer_id, "error": str(exc)},
        )
        raise


@celery_app.task(
    name="workers.lead_worker.decay_leads",
    queue="engagement",
)
def decay_leads() -> None:
    """Jalankan auto-decay semua lead. Dipanggil Celery Beat tiap hari."""

    async def _run() -> None:
        from sqlalchemy.pool import NullPool
        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
        from app.core.config import get_settings
        from app.services.lead_service import run_decay

        import app.models.user  # noqa: F401

        _settings = get_settings()
        _engine = create_async_engine(_settings.DATABASE_URL, poolclass=NullPool)
        _Session = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)

        try:
            async with _Session() as session:
                async with session.begin():
                    count = await run_decay(session)
            logger.info("decay_leads completed", extra={"updated": count})
        finally:
            await _engine.dispose()

    try:
        asyncio.run(_run())
    except Exception as exc:
        logger.error("decay_leads failed", extra={"error": str(exc)})
        raise
```

- [ ] **Step 4: Update `workers/celery_app.py` — tambah lead_worker + beat_schedule**

```python
from celery import Celery
from celery.schedules import crontab

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "reseller_ai",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "workers.discovery_worker",
        "workers.content_worker",
        "workers.engagement_worker",
        "workers.conversion_worker",
        "workers.lead_worker",      # tambah ini
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Jakarta",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_routes={
        "workers.discovery_worker.*": {"queue": "discovery"},
        "workers.content_worker.*": {"queue": "content"},
        "workers.engagement_worker.*": {"queue": "engagement"},
        "workers.conversion_worker.*": {"queue": "conversion"},
        "workers.lead_worker.*": {"queue": "engagement"},   # tambah ini
    },
)

celery_app.conf.beat_schedule = {
    "decay-leads-daily": {
        "task": "workers.lead_worker.decay_leads",
        "schedule": crontab(hour=20, minute=0),  # 03:00 WIB = 20:00 UTC
    },
}
```

- [ ] **Step 5: Update `workers/engagement_worker.py` — chain classify_lead setelah commit**

Di fungsi `_run()` dalam `process_facebook_event`, ubah blok `async with _Session()` agar capture `customer_id` dan panggil `classify_lead.delay()` **setelah** `session.begin()` selesai:

```python
async def _run() -> None:
    from sqlalchemy.pool import NullPool
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
    from app.core.config import get_settings
    from app.services.engagement_service import (
        process_facebook_comment,
        process_messenger_message,
    )

    import app.models.user  # noqa: F401

    _settings = get_settings()
    _engine = create_async_engine(_settings.DATABASE_URL, poolclass=NullPool)
    _Session = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)

    customer_id: str | None = None

    try:
        async with _Session() as session:
            async with session.begin():
                if channel_type == "comment":
                    customer_id = await process_facebook_comment(tenant_id, event, session)
                elif channel_type == "dm":
                    customer_id = await process_messenger_message(tenant_id, event, session)
                else:
                    logger.warning(
                        "Unknown channel_type",
                        extra={"channel_type": channel_type, "tenant_id": tenant_id},
                    )
        # Conversation sudah committed — chain lead classification
        if customer_id is not None:
            from workers.lead_worker import classify_lead
            classify_lead.delay(tenant_id, customer_id)
    finally:
        await _engine.dispose()
```

- [ ] **Step 6: Verifikasi import tidak error**

```bash
cd backend && python -c "from workers.lead_worker import classify_lead, decay_leads; print('OK')"
```

Expected: `OK`

- [ ] **Step 7: Commit**

```bash
git add workers/lead_worker.py workers/celery_app.py workers/engagement_worker.py \
        app/services/engagement_service.py app/core/feature_flags.py
git commit -m "feat: lead_worker (classify_lead, decay_leads) + engagement_worker chain"
```

---

## Task 5: Leads Router + Schemas

**Files:**
- Create: `app/schemas/lead.py`
- Create: `app/routers/leads.py`
- Modify: `app/main.py`

**Interfaces:**
- Consumes: `Lead` model (Task 1), `archive_lead`, `resolve_lead` (Task 3)
- Produces:
  - `GET /api/v1/leads` → `APIResponse[list[LeadResponse]]`
  - `PATCH /api/v1/leads/{id}/archive` → `APIResponse[LeadResponse]`
  - `PATCH /api/v1/leads/{id}/resolve` → `APIResponse[LeadResponse]`

- [ ] **Step 1: Buat `app/schemas/lead.py`**

```python
import uuid
from datetime import datetime

from pydantic import BaseModel


class LeadCustomerInfo(BaseModel):
    name: str | None
    platform: str

    model_config = {"from_attributes": True}


class LeadResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    customer_id: uuid.UUID
    tier: str
    tier_reason: str | None
    interaction_count: int
    last_interaction: datetime | None
    status: str
    resolved_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
```

- [ ] **Step 2: Buat `app/routers/leads.py`**

```python
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.models.customer import Customer
from app.models.lead import Lead
from app.schemas.base import APIResponse
from app.schemas.lead import LeadResponse
from app.services.lead_service import archive_lead, resolve_lead

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/leads", tags=["leads"])


@router.get("", response_model=APIResponse[list[LeadResponse]])
async def list_leads(
    request: Request,
    tier: str | None = Query(None, pattern="^(hot|warm|cold)$"),
    status: str | None = Query(None, pattern="^(active|archived|resolved)$"),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db_session),
):
    tenant_id: str = request.state.tenant_id

    stmt = (
        select(Lead)
        .where(Lead.tenant_id == uuid.UUID(tenant_id))  # RULE-03
        .order_by(Lead.last_interaction.desc().nulls_last())
        .limit(limit)
    )
    if tier is not None:
        stmt = stmt.where(Lead.tier == tier)
    if status is not None:
        stmt = stmt.where(Lead.status == status)
    else:
        # Default: hanya tampilkan active
        stmt = stmt.where(Lead.status == "active")

    result = await db.execute(stmt)
    leads = result.scalars().all()

    return APIResponse(data=[LeadResponse.model_validate(lead) for lead in leads])


@router.patch("/{lead_id}/archive", response_model=APIResponse[LeadResponse])
async def archive_lead_endpoint(
    lead_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    tenant_id: str = request.state.tenant_id
    lead = await archive_lead(lead_id, tenant_id, db)
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead tidak ditemukan.")
    return APIResponse(data=LeadResponse.model_validate(lead))


@router.patch("/{lead_id}/resolve", response_model=APIResponse[LeadResponse])
async def resolve_lead_endpoint(
    lead_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    tenant_id: str = request.state.tenant_id
    lead = await resolve_lead(lead_id, tenant_id, db)
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead tidak ditemukan.")
    return APIResponse(data=LeadResponse.model_validate(lead))
```

- [ ] **Step 3: Register router di `app/main.py`**

Tambahkan import dan `include_router`:

```python
from app.routers import auth, conversations, features, webhooks, leads  # tambah leads

# Di bawah routers yang sudah ada:
app.include_router(leads.router)
```

- [ ] **Step 4: Verifikasi endpoint terdaftar**

```bash
cd backend && python -c "
from app.main import app
routes = [r.path for r in app.routes]
assert '/api/v1/leads' in routes, 'Route tidak ditemukan!'
print('Routes OK:', [r for r in routes if 'leads' in r])
"
```

Expected: `Routes OK: ['/api/v1/leads', '/api/v1/leads/{lead_id}/archive', '/api/v1/leads/{lead_id}/resolve']`

- [ ] **Step 5: Commit**

```bash
git add app/schemas/lead.py app/routers/leads.py app/main.py
git commit -m "feat: leads router GET /leads + PATCH archive/resolve"
```

---

## Task 6: Frontend — `useLeads` Hook + Leads Page

**Files:**
- Create: `src/hooks/useLeads.ts`
- Create: `src/pages/Leads.tsx`
- Modify: `src/App.tsx`

**Interfaces:**
- Consumes: `GET /api/v1/leads`, `PATCH /api/v1/leads/{id}/archive`, `PATCH /api/v1/leads/{id}/resolve`
- Produces: route `/leads` → `<Leads />`

- [ ] **Step 1: Buat `src/hooks/useLeads.ts`**

```typescript
import { useEffect, useState } from "react";
import api from "@/lib/api";

export interface LeadResponse {
  id: string;
  tenant_id: string;
  customer_id: string;
  tier: "hot" | "warm" | "cold";
  tier_reason: string | null;
  interaction_count: number;
  last_interaction: string | null;
  status: "active" | "archived" | "resolved";
  resolved_at: string | null;
  created_at: string;
  updated_at: string;
}

type TierFilter = "all" | "hot" | "warm" | "cold" | "archived";

export function useLeads(filter: TierFilter) {
  const [leads, setLeads] = useState<LeadResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const params: Record<string, string> = {};
    if (filter === "archived") {
      params.status = "archived";
    } else if (filter !== "all") {
      params.tier = filter;
    }
    // default: status=active (server default)

    function fetchLeads() {
      api
        .get<{ data: LeadResponse[] }>("/leads", { params })
        .then((res) => {
          setLeads(res.data.data);
          setIsLoading(false);
        })
        .catch(() => setIsLoading(false));
    }

    setIsLoading(true);
    fetchLeads();
    const timer = setInterval(fetchLeads, 30_000);
    return () => clearInterval(timer);
  }, [filter]);

  async function archiveLead(id: string) {
    setLeads((prev) => prev.filter((l) => l.id !== id));
    try {
      await api.patch(`/leads/${id}/archive`);
    } catch {
      // Rollback tidak perlu — next poll akan restore state dari server
    }
  }

  async function resolveLead(id: string) {
    setLeads((prev) => prev.filter((l) => l.id !== id));
    try {
      await api.patch(`/leads/${id}/resolve`);
    } catch {
      // Rollback tidak perlu — next poll akan restore state dari server
    }
  }

  return { leads, isLoading, archiveLead, resolveLead };
}
```

- [ ] **Step 2: Buat `src/pages/Leads.tsx`**

```tsx
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useAuth } from "@/hooks/useAuth";
import { useLeads, type LeadResponse } from "@/hooks/useLeads";

type TierFilter = "all" | "hot" | "warm" | "cold" | "archived";

const FILTER_LABELS: Record<TierFilter, string> = {
  all: "Semua",
  hot: "Hot",
  warm: "Warm",
  cold: "Cold",
  archived: "Arsip",
};

const TIER_BADGE: Record<string, string> = {
  hot: "bg-red-50 text-red-700 border border-red-200",
  warm: "bg-amber-50 text-amber-700 border border-amber-200",
  cold: "bg-slate-50 text-slate-500 border border-slate-200",
};

const PLATFORM_ICON: Record<string, string> = {
  facebook: "🌐",
  messenger: "💬",
  instagram: "📸",
  whatsapp: "📱",
};

function relativeTime(iso: string | null) {
  if (!iso) return "—";
  const diff = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (diff < 60) return `${diff}d lalu`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m lalu`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}j lalu`;
  return `${Math.floor(diff / 86400)}h lalu`;
}

function TierBadge({ tier }: { tier: string }) {
  return (
    <span
      className={`inline-flex items-center rounded px-2 py-0.5 text-xs font-medium ${TIER_BADGE[tier] ?? "bg-slate-50 text-slate-500 border border-slate-200"}`}
    >
      {tier.charAt(0).toUpperCase() + tier.slice(1)}
    </span>
  );
}

function LeadRow({
  lead,
  onArchive,
  onResolve,
}: {
  lead: LeadResponse;
  onArchive: (id: string) => void;
  onResolve: (id: string) => void;
}) {
  return (
    <TableRow className="group hover:bg-slate-50 transition-none">
      <TableCell className="font-medium text-slate-800">
        {lead.customer_id.slice(0, 8)}…
      </TableCell>
      <TableCell className="text-slate-500 text-sm">
        —
      </TableCell>
      <TableCell>
        <TierBadge tier={lead.tier} />
      </TableCell>
      <TableCell className="text-slate-500 tabular-nums">
        {lead.interaction_count}x
      </TableCell>
      <TableCell className="text-slate-400 text-sm">
        {relativeTime(lead.last_interaction)}
      </TableCell>
      <TableCell>
        <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          <Button
            variant="ghost"
            size="sm"
            className="h-7 px-2 text-xs text-slate-500 hover:text-slate-800"
            onClick={() => onArchive(lead.id)}
          >
            Arsip
          </Button>
          <Button
            variant="ghost"
            size="sm"
            className="h-7 px-2 text-xs text-slate-500 hover:text-slate-800"
            onClick={() => onResolve(lead.id)}
          >
            Selesai
          </Button>
        </div>
      </TableCell>
    </TableRow>
  );
}

export default function Leads() {
  const { logout } = useAuth();
  const [filter, setFilter] = useState<TierFilter>("all");
  const { leads, isLoading, archiveLead, resolveLead } = useLeads(filter);

  const hotCount = leads.filter((l) => l.tier === "hot" && l.status === "active").length;

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="flex items-center justify-between border-b border-slate-200 bg-white px-6 py-3 shadow-sm">
        <div className="flex items-center gap-3">
          <span className="text-sm font-semibold text-slate-900">
            Reseller AI — Leads
          </span>
          {hotCount > 0 && (
            <span className="inline-flex items-center rounded px-2 py-0.5 text-xs font-medium bg-red-50 text-red-700 border border-red-200">
              {hotCount} hot
            </span>
          )}
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={logout}
          className="text-slate-500 hover:text-slate-900"
        >
          Keluar
        </Button>
      </header>

      <main className="mx-auto max-w-6xl px-6 py-6">
        <div className="mb-4 flex items-center justify-between">
          <div className="flex gap-2">
            {(["all", "hot", "warm", "cold", "archived"] as TierFilter[]).map((f) => (
              <Button
                key={f}
                size="sm"
                variant={filter === f ? "default" : "outline"}
                onClick={() => setFilter(f)}
                className={
                  filter === f
                    ? "bg-slate-900 text-white hover:bg-slate-800"
                    : "border-slate-300 text-slate-600 hover:bg-slate-50"
                }
              >
                {FILTER_LABELS[f]}
              </Button>
            ))}
          </div>
          <span className="text-xs text-slate-400">{leads.length} leads</span>
        </div>

        <div className="rounded-lg border border-slate-200 bg-white shadow-sm overflow-hidden">
          {isLoading ? (
            <div className="flex items-center justify-center py-16 text-sm text-slate-400">
              Memuat…
            </div>
          ) : leads.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-sm text-slate-400">
              <p>Belum ada lead.</p>
              <p className="mt-1 text-xs">Lead muncul otomatis saat ada interaksi masuk.</p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow className="bg-slate-50 hover:bg-slate-50">
                  <TableHead className="text-xs font-medium text-slate-500 uppercase tracking-wide">Customer</TableHead>
                  <TableHead className="text-xs font-medium text-slate-500 uppercase tracking-wide">Platform</TableHead>
                  <TableHead className="text-xs font-medium text-slate-500 uppercase tracking-wide">Tier</TableHead>
                  <TableHead className="text-xs font-medium text-slate-500 uppercase tracking-wide">Interaksi</TableHead>
                  <TableHead className="text-xs font-medium text-slate-500 uppercase tracking-wide">Terakhir aktif</TableHead>
                  <TableHead />
                </TableRow>
              </TableHeader>
              <TableBody>
                {leads.map((lead) => (
                  <LeadRow
                    key={lead.id}
                    lead={lead}
                    onArchive={archiveLead}
                    onResolve={resolveLead}
                  />
                ))}
              </TableBody>
            </Table>
          )}
        </div>
      </main>
    </div>
  );
}
```

- [ ] **Step 3: Update `src/App.tsx` — tambah route `/leads`**

```tsx
import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import Landing from "@/pages/Landing";
import Privacy from "@/pages/Privacy";
import Terms from "@/pages/Terms";
import Login from "@/pages/Login";
import Inbox from "@/pages/Inbox";
import Leads from "@/pages/Leads";

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isLoading, isAuthenticated } = useAuth();
  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center text-sm text-muted-foreground">
        Memuat...
      </div>
    );
  }
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/privacy" element={<Privacy />} />
      <Route path="/terms" element={<Terms />} />
      <Route path="/login" element={<Login />} />
      <Route
        path="/inbox"
        element={
          <ProtectedRoute>
            <Inbox />
          </ProtectedRoute>
        }
      />
      <Route
        path="/leads"
        element={
          <ProtectedRoute>
            <Leads />
          </ProtectedRoute>
        }
      />
    </Routes>
  );
}
```

- [ ] **Step 4: Tambah nav link "Leads" di `src/pages/Inbox.tsx`**

Di header Inbox, tambahkan link ke `/leads` sejajar dengan judul:

```tsx
// Tambahkan import di atas file:
import { Link } from "react-router-dom";

// Di dalam <header>, setelah badge escalation (atau sebelum tombol Keluar):
<Link
  to="/leads"
  className="text-xs text-slate-500 hover:text-slate-800 underline-offset-2 hover:underline"
>
  Leads
</Link>
```

- [ ] **Step 5: Type check frontend**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors

- [ ] **Step 6: Commit**

```bash
git add src/hooks/useLeads.ts src/pages/Leads.tsx src/App.tsx src/pages/Inbox.tsx
git commit -m "feat: Leads page + useLeads hook + route /leads"
```

---

## Self-Review Checklist

Sebelum declare selesai, verifikasi:

- [ ] `pytest tests/test_lead_service.py -v` → semua PASSED
- [ ] `python -c "from workers.lead_worker import classify_lead, decay_leads; print('OK')"` → OK
- [ ] `cd frontend && npx tsc --noEmit` → no errors
- [ ] `GET /api/v1/leads` returns 200 (dengan tenant aktif + token valid)
- [ ] `PATCH /api/v1/leads/{id}/archive` returns 200 atau 404 (bukan 500)
- [ ] Lead muncul di Leads page setelah ada conversation masuk di Inbox

> **Catatan:** Kolom Platform di Leads page menampilkan `—` untuk saat ini. Info platform customer membutuhkan join ke tabel `customers` yang bisa ditambahkan di iterasi berikutnya jika diperlukan.
