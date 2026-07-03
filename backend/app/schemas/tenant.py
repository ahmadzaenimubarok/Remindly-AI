import uuid

from pydantic import BaseModel, EmailStr


class TenantResponse(BaseModel):
    id: uuid.UUID
    name: str
    email: EmailStr
    plan: str

    model_config = {"from_attributes": True}
