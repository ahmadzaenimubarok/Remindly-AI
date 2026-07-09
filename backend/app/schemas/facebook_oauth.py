from pydantic import BaseModel, Field


class FacebookOAuthCallbackRequest(BaseModel):
    code: str = Field(..., min_length=1, description="Authorization code dari Facebook")


class FacebookPageResponse(BaseModel):
    page_id: str
    page_name: str
    access_token: str


class FacebookConnectRequest(BaseModel):
    page_id: str = Field(..., min_length=1)
    page_name: str = Field(default="")
    access_token: str = Field(..., min_length=1)


class FacebookConnectionResponse(BaseModel):
    connected: bool
    page_id: str | None = None
    page_name: str | None = None
    facebook_user_id: str | None = None
