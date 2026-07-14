import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.schemas.base import APIResponse
from app.schemas.product import CreateProductRequest, ProductResponse, UpdateProductRequest
from app.schemas.shopify import ShopifyImportResponse
from app.services.product_service import (
    create_product,
    delete_product,
    import_from_shopify,
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
    deleted = await delete_product(product_id, tenant_id, db)
    if not deleted:
        raise HTTPException(status_code=404, detail="Produk tidak ditemukan.")
    return APIResponse(data=None, message="Produk berhasil dihapus.")


@router.post("/shopify/import", response_model=APIResponse[ShopifyImportResponse])
async def shopify_import_endpoint(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """Import produk dari Shopify ke database."""
    tenant_id: str = request.state.tenant_id
    try:
        result = await import_from_shopify(tenant_id, db)
        return APIResponse(
            data=ShopifyImportResponse(**result),
            message=f"Import selesai: {result['imported']} produk diimport, {result['updated']} produk diupdate.",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Shopify import error")
        raise HTTPException(status_code=500, detail="Gagal import produk dari Shopify.")
