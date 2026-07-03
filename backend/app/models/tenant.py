import uuid

from sqlalchemy import JSON, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Tenant(Base, TimestampMixin):
    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    plan: Mapped[str] = mapped_column(String(50), default="free", nullable=False)
    plan_expires_at: Mapped[str | None] = mapped_column(nullable=True)
    ai_config: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    users: Mapped[list["User"]] = relationship("User", back_populates="tenant")
