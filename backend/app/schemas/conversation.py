import uuid
from datetime import datetime

from pydantic import BaseModel


class ConversationResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    customer_id: uuid.UUID
    session_id: uuid.UUID | None
    platform: str
    channel_type: str
    message_in: str | None
    message_out: str | None
    intent: str | None
    sentiment: str | None
    is_human_takeover: bool
    escalation_reason: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ThreadMessage(BaseModel):
    id: uuid.UUID
    message_in: str | None
    message_out: str | None
    intent: str | None
    sentiment: str | None
    is_human_takeover: bool
    escalation_reason: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ThreadResponse(BaseModel):
    session_id: uuid.UUID
    customer_id: uuid.UUID
    customer_name: str | None
    platform: str
    channel_type: str
    status: str
    is_continuation: bool
    prior_session_id: uuid.UUID | None
    prior_session_date: datetime | None
    message_count: int
    has_human_takeover: bool
    last_message_at: datetime
    messages: list[ThreadMessage]


class TakeoverRequest(BaseModel):
    is_human_takeover: bool
