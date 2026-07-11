from pydantic import BaseModel, Field


class InstagramConnectRequest(BaseModel):
    page_id: str = Field(..., min_length=1)
    page_name: str = Field(default="")
    page_token: str = Field(..., min_length=1)
    instagram_account_id: str = Field(..., min_length=1)
    instagram_username: str = Field(default="")


class InstagramAccountInfo(BaseModel):
    page_id: str
    page_name: str
    page_token: str
    instagram_account_id: str
    instagram_username: str
    instagram_name: str
