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
    db.delete = AsyncMock()
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

    body = CreateProductRequest(name="Sepatu Lari", base_price=Decimal("150000"))
    result = await create_product(tenant_id, body, db)

    assert result.name == "Sepatu Lari"
    assert result.tenant_id == uuid.UUID(tenant_id)
    db.add.assert_called_once()
    db.flush.assert_called_once()


@pytest.mark.asyncio
async def test_list_products_filters_by_tenant():
    tenant_id = str(uuid.uuid4())
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
