"""
Seed script — isi data demo untuk development.

Usage (dari folder backend/):
    python scripts/seed.py
    python scripts/seed.py --reset   # hapus semua data dulu lalu seed ulang

Akan membuat:
  - 1 tenant: Demo Toko
  - 1 user  : admin@demo.com / password: demo1234
  - 5 produk contoh (fashion/tas)
  - 3 customer (Instagram)
  - 5 conversation per customer
"""

import argparse
import asyncio
import sys
from datetime import datetime, timezone

from passlib.context import CryptContext
from sqlalchemy import delete, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

sys.path.insert(0, ".")  # pastikan app dapat diimport dari backend/

from app.core.config import get_settings
from app.models.base import Base  # noqa: F401 — pastikan semua model ter-register
from app.models.conversation import Conversation
from app.models.customer import Customer
from app.models.product import Product
from app.models.tenant import Tenant
from app.models.user import User

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------

TENANT = {
    "name": "Demo Toko",
    "email": "tenant@demo.com",
    "plan": "starter",
    "ai_config": {
        "tone": "friendly",
        "language": "id",
        "auto_reply": True,
    },
}

ADMIN_USER = {
    "email": "admin@demo.com",
    "password": "demo1234",
    "role": "tenant_user",
    "is_active": True,
}

PRODUCTS = [
    {
        "name": "Tas Selempang Canvas Vintage",
        "category": "Tas",
        "description": "Tas selempang bahan canvas tebal, cocok untuk daily use. Tersedia dalam 4 warna.",
        "base_price": "85000",
        "margin_estimate": "35",
        "supplier_link": "https://supplier.example.com/tas-canvas-vintage",
        "status": "active",
    },
    {
        "name": "Dompet Kulit Minimalis",
        "category": "Aksesoris",
        "description": "Dompet slim dari kulit PU berkualitas, muat 8 kartu + uang tunai.",
        "base_price": "55000",
        "margin_estimate": "40",
        "supplier_link": "https://supplier.example.com/dompet-kulit",
        "status": "active",
    },
    {
        "name": "Tote Bag Kanvas Polos",
        "category": "Tas",
        "description": "Tote bag serba guna, bisa dijadikan media custom print.",
        "base_price": "35000",
        "margin_estimate": "50",
        "affiliate_link": "https://affiliate.example.com/totebag",
        "status": "active",
    },
    {
        "name": "Kacamata Baca +1.5",
        "category": "Aksesoris",
        "description": "Frame bulat retro, lensa anti-silau. Cocok buat kerja di depan laptop.",
        "base_price": "45000",
        "margin_estimate": "45",
        "status": "active",
    },
    {
        "name": "Jam Tangan Casual Unisex",
        "category": "Jam",
        "description": "Desain minimalis, water resistant 3ATM, strap silikon.",
        "base_price": "120000",
        "margin_estimate": "30",
        "status": "inactive",
    },
]

CUSTOMERS = [
    {
        "platform_user_id": "ig_user_001",
        "platform": "instagram",
        "name": "Rina Pratiwi",
        "handle": "@rina.pratiwi",
    },
    {
        "platform_user_id": "ig_user_002",
        "platform": "instagram",
        "name": "Budi Santoso",
        "handle": "@budi_s",
    },
    {
        "platform_user_id": "ig_user_003",
        "platform": "instagram",
        "name": "Mega Dewi",
        "handle": "@mega.dewi_shop",
    },
]

CONVERSATIONS = [
    # Rina — nanya produk, akhirnya order
    [
        ("in",  "Kak, tas canvas yang vintage masih ada stoknya?"),
        ("out", "Hai Kak Rina! Masih ada, tersedia dalam 4 warna: hitam, coklat, olive, dan navy. Mau warna apa?"),
        ("in",  "Yang olive ada nggak? Mau buat ke kampus"),
        ("out", "Ada Kak! Stok olive tinggal 3 pcs. Harga Rp 135.000 sudah termasuk ongkir Jabodetabek."),
        ("in",  "Oke deh, mau pesan 1. Bayar transfer ya"),
    ],
    # Budi — nanya harga, nggak jadi
    [
        ("in",  "Min harga dompet kulit berapa?"),
        ("out", "Halo Kak! Dompet Kulit Minimalis kami Rp 95.000. Bisa muat 8 kartu + uang tunai."),
        ("in",  "Aduh mahal juga ya"),
        ("out", "Kualitasnya worth it Kak, bahannya PU premium. Kalau mau bisa request warna juga lho!"),
        ("in",  "Iya deh nanti pikir-pikir dulu"),
    ],
    # Mega — komplain & eskalasi
    [
        ("in",  "Hai, aku udah order tote bag 3 hari lalu tapi belum dikirim"),
        ("out", "Hai Kak Mega, maaf ya! Boleh share no. resi atau nomor ordernya?"),
        ("in",  "Nomornya OD-2024-887. Ini udah lama banget"),
        ("out", "Sedang aku cek sekarang Kak, satu moment ya..."),
        ("in",  "Kalau nggak dikirim hari ini aku mau refund aja"),
    ],
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def reset_data(session: AsyncSession) -> None:
    print("Menghapus data lama...")
    await session.execute(delete(Conversation))
    await session.execute(delete(Customer))
    await session.execute(delete(Product))
    await session.execute(delete(User).where(User.role != "super_admin"))
    await session.execute(delete(Tenant).where(Tenant.email == TENANT["email"]))
    print("  selesai.")


async def seed(session: AsyncSession) -> None:
    print("Membuat tenant...")
    tenant = Tenant(**TENANT)
    session.add(tenant)
    await session.flush()  # dapatkan tenant.id

    print(f"  Tenant: {tenant.name} (id={tenant.id})")

    print("Membuat user admin...")
    user = User(
        tenant_id=tenant.id,
        email=ADMIN_USER["email"],
        password_hash=pwd_ctx.hash(ADMIN_USER["password"]),
        role=ADMIN_USER["role"],
        is_active=ADMIN_USER["is_active"],
    )
    session.add(user)

    print("Membuat produk...")
    for p in PRODUCTS:
        session.add(Product(tenant_id=tenant.id, **p))

    print("Membuat customer & conversation...")
    for i, cdata in enumerate(CUSTOMERS):
        customer = Customer(tenant_id=tenant.id, **cdata)
        session.add(customer)
        await session.flush()

        convs = CONVERSATIONS[i] if i < len(CONVERSATIONS) else []
        for direction, text_body in convs:
            conv = Conversation(
                tenant_id=tenant.id,
                customer_id=customer.id,
                platform="instagram",
                channel_type="dm",
                message_in=text_body if direction == "in" else None,
                message_out=text_body if direction == "out" else None,
                intent="inquiry",
                sentiment="neutral",
            )
            session.add(conv)

    print()
    print("=" * 50)
    print("Seed selesai!")
    print(f"  URL    : http://localhost:5173")
    print(f"  Email  : {ADMIN_USER['email']}")
    print(f"  Password: {ADMIN_USER['password']}")
    print("=" * 50)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main(reset: bool) -> None:
    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with Session() as session:
        async with session.begin():
            if reset:
                await reset_data(session)
            await seed(session)

    await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed demo data")
    parser.add_argument("--reset", action="store_true", help="Hapus data lama sebelum seed")
    args = parser.parse_args()

    asyncio.run(main(reset=args.reset))
