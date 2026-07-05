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
