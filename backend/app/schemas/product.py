import uuid
from decimal import Decimal

from pydantic import BaseModel, Field


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
