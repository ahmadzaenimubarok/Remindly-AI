"""
Seed Stripe Products & Prices untuk development/staging.

Idempotent: cek metadata 'reseller_plan' dulu, skip kalau sudah ada.
Setelah selesai, update PLAN_PRICES di billing_service.py otomatis.

Usage (dari folder backend/):
    python scripts/seed_stripe.py
    python scripts/seed_stripe.py --dry-run   # tampilkan rencana tanpa eksekusi
"""

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, ".")

import stripe
from app.core.config import get_settings

BILLING_SERVICE = Path("app/services/billing_service.py")

PLANS = [
    {
        "key": "starter",
        "name": "Remindly AI — Starter",
        "description": "Instagram & TikTok reply, content publish, product discovery",
        "amount": 9_900_000,   # Stripe IDR pakai sen: Rp 99.000 × 100
        "currency": "idr",
        "interval": "month",
    },
    {
        "key": "pro",
        "name": "Remindly AI — Pro",
        "description": "Semua fitur Starter + Facebook & WhatsApp, lead classification, analytics",
        "amount": 29_900_000,  # Rp 299.000 × 100
        "currency": "idr",
        "interval": "month",
    },
    {
        "key": "enterprise",
        "name": "Remindly AI — Enterprise",
        "description": "Unlimited channels, dedicated support, custom SLA",
        "amount": 299_900_000, # Rp 2.999.000 × 100
        "currency": "idr",
        "interval": "year",
    },
]


def find_existing_product(plan_key: str) -> stripe.Product | None:
    products = stripe.Product.search(
        query=f'metadata["reseller_plan"]:"{plan_key}"',
        limit=1,
    )
    return products.data[0] if products.data else None


def find_existing_price(product_id: str) -> stripe.Price | None:
    prices = stripe.Price.list(product=product_id, active=True, limit=1)
    return prices.data[0] if prices.data else None


def update_billing_service(price_map: dict[str, str]) -> None:
    src = BILLING_SERVICE.read_text()
    new_block = (
        'PLAN_PRICES: dict[str, str] = {\n'
        f'    "starter": "{price_map["starter"]}",\n'
        f'    "pro": "{price_map["pro"]}",\n'
        f'    "enterprise": "{price_map["enterprise"]}",\n'
        '}'
    )
    updated = re.sub(
        r'PLAN_PRICES: dict\[str, str\] = \{[^}]+\}',
        new_block,
        src,
        flags=re.DOTALL,
    )
    BILLING_SERVICE.write_text(updated)


def run(dry_run: bool) -> None:
    settings = get_settings()
    stripe.api_key = settings.STRIPE_SECRET_KEY

    print(f"Mode  : {'DRY RUN' if dry_run else 'LIVE'}")
    print(f"Stripe: {'test' if 'test' in settings.STRIPE_SECRET_KEY else 'live'} mode")
    print()

    price_map: dict[str, str] = {}

    for plan in PLANS:
        key = plan["key"]
        print(f"[{key}]")

        existing_product = find_existing_product(key)
        if existing_product:
            print(f"  Product sudah ada: {existing_product.id} — skip buat ulang")
            product_id = existing_product.id
        else:
            if dry_run:
                print(f"  Akan buat Product: {plan['name']}")
                price_map[key] = f"price_DRY_RUN_{key.upper()}"
                continue
            product = stripe.Product.create(
                name=plan["name"],
                description=plan["description"],
                metadata={"reseller_plan": key},
            )
            product_id = product.id
            print(f"  Product dibuat: {product_id}")

        existing_price = find_existing_price(product_id)
        if existing_price:
            print(f"  Price sudah ada: {existing_price.id} ({existing_price.unit_amount} {existing_price.currency}/{existing_price.recurring.interval}) — skip")
            price_map[key] = existing_price.id
        else:
            if dry_run:
                print(f"  Akan buat Price: {plan['amount']} {plan['currency']}/{plan['interval']}")
                price_map[key] = f"price_DRY_RUN_{key.upper()}"
                continue
            price = stripe.Price.create(
                product=product_id,
                unit_amount=plan["amount"],
                currency=plan["currency"],
                recurring={"interval": plan["interval"]},
                metadata={"reseller_plan": key},
            )
            price_map[key] = price.id
            print(f"  Price dibuat: {price.id}")

    print()
    print("Price IDs:")
    for k, v in price_map.items():
        print(f"  {k}: {v}")

    if not dry_run:
        print()
        print(f"Update {BILLING_SERVICE} ...")
        update_billing_service(price_map)
        print("  PLAN_PRICES diperbarui.")

    print()
    print("Selesai!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed Stripe Products & Prices")
    parser.add_argument("--dry-run", action="store_true", help="Tampilkan rencana tanpa eksekusi ke Stripe")
    args = parser.parse_args()

    run(dry_run=args.dry_run)
