import uuid
from datetime import datetime

from pydantic import BaseModel


class LeadResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    customer_id: uuid.UUID
    tier: str
    tier_reason: str | None
    interaction_count: int
    last_interaction: datetime | None
    status: str
    resolved_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
