from pydantic import BaseModel, Field


class SaveFBTokenRequest(BaseModel):
    page_token: str = Field(..., min_length=10)
    page_id: str = Field(..., min_length=1)


class SaveIGTokenRequest(BaseModel):
    page_token: str = Field(..., min_length=10)
    instagram_account_id: str = Field(..., min_length=1)


class SettingsResponse(BaseModel):
    facebook_connected: bool
    instagram_connected: bool
    shopify_connected: bool = False
    product_count: int
