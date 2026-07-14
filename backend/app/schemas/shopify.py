from pydantic import BaseModel, Field


class ShopifyConnectRequest(BaseModel):
    shop_domain: str = Field(..., description="Shopify shop domain (e.g., my-store.myshopify.com)")
    access_token: str = Field(..., description="Shopify Admin API access token")
    shop_name: str = Field(..., description="Shop name")


class ShopifyImportResponse(BaseModel):
    imported: int = Field(..., description="Number of products imported")
    updated: int = Field(..., description="Number of products updated")
    errors: list[str] = Field(default_factory=list, description="Any errors during import")
