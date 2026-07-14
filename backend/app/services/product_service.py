import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product
from app.schemas.product import CreateProductRequest, UpdateProductRequest
from app.services.shopify_oauth_service import get_shopify_credentials
from app.services.shopify_service import fetch_products, transform_shopify_product

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


async def import_from_shopify(tenant_id: str, db: AsyncSession) -> dict:
    """Import produk dari Shopify ke database."""
    # 1. Ambil kredensial Shopify
    credentials = await get_shopify_credentials(tenant_id, db)
    if not credentials:
        raise ValueError("Shopify belum terhubung.")

    shop_domain = credentials["shop_domain"]
    access_token = credentials["access_token"]

    # 2. Fetch produk dari Shopify
    shopify_products = await fetch_products(shop_domain, access_token)

    imported = 0
    updated = 0
    errors = []

    for shopify_product in shopify_products:
        try:
            # Transform data
            product_data = transform_shopify_product(shopify_product, shop_domain)
            shopify_product_id = product_data["shopify_product_id"]

            # Cek apakah produk sudah ada
            existing_result = await db.execute(
                select(Product).where(
                    Product.tenant_id == uuid.UUID(tenant_id),
                    Product.shopify_product_id == shopify_product_id,
                )
            )
            existing_product = existing_result.scalar_one_or_none()

            if existing_product:
                # Update produk yang sudah ada
                existing_product.name = product_data["name"]
                existing_product.description = product_data["description"]
                existing_product.base_price = product_data["base_price"]
                existing_product.category = product_data["category"]
                existing_product.status = product_data["status"]
                existing_product.supplier_link = product_data["product_url"]
                existing_product.shopify_synced_at = datetime.now(timezone.utc)
                updated += 1
            else:
                # Buat produk baru
                new_product = Product(
                    tenant_id=uuid.UUID(tenant_id),
                    name=product_data["name"],
                    description=product_data["description"],
                    base_price=product_data["base_price"],
                    category=product_data["category"],
                    status=product_data["status"],
                    supplier_link=product_data["product_url"],
                    shopify_product_id=shopify_product_id,
                    shopify_synced_at=datetime.now(timezone.utc),
                    source="shopify",
                )
                db.add(new_product)
                imported += 1

        except Exception as e:
            error_msg = f"Error importing product {shopify_product.get('title', 'unknown')}: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)

    await db.flush()
    logger.info(
        "Shopify import completed",
        extra={
            "tenant_id": tenant_id,
            "imported": imported,
            "updated": updated,
            "errors": len(errors),
        },
    )

    return {
        "imported": imported,
        "updated": updated,
        "errors": errors,
    }
