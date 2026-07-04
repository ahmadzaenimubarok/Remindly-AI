import uuid

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Conversation(Base, TimestampMixin):
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    channel_type: Mapped[str] = mapped_column(String(50), nullable=False)
    platform_message_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True
    )
    message_in: Mapped[str | None] = mapped_column(Text, nullable=True)
    message_out: Mapped[str | None] = mapped_column(Text, nullable=True)
    intent: Mapped[str | None] = mapped_column(String(50), nullable=True)
    sentiment: Mapped[str | None] = mapped_column(String(20), nullable=True)
    is_human_takeover: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    escalation_reason: Mapped[str | None] = mapped_column(String(100), nullable=True)
