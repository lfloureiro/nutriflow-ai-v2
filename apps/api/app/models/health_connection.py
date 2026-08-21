import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.health_measurement import HealthMeasurement
    from app.models.person import Person


class HealthConnection(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "health_connections"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'active', 'paused', 'error', 'revoked')",
            name="ck_health_connections_status_valid",
        ),
        CheckConstraint(
            "revoked_at IS NULL OR status = 'revoked'",
            name="ck_health_connections_revoked_status_valid",
        ),
        UniqueConstraint(
            "person_id",
            "provider",
            "connection_key",
            name="uq_health_connections_person_provider_key",
        ),
        Index(
            "ix_health_connections_person_provider_status",
            "person_id",
            "provider",
            "status",
        ),
    )

    person_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("persons.id", ondelete="CASCADE"),
        nullable=False,
    )

    provider: Mapped[str] = mapped_column(String(40), nullable=False)
    connection_key: Mapped[str] = mapped_column(String(120), nullable=False)
    connection_kind: Mapped[str] = mapped_column(String(32), nullable=False)

    status: Mapped[str] = mapped_column(String(24), nullable=False, default="pending")
    permissions: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)

    provider_account_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    credential_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    provider_metadata: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)

    sync_cursor: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_sync_attempt_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_successful_sync_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    person: Mapped["Person"] = relationship(back_populates="health_connections")
    health_measurements: Mapped[list["HealthMeasurement"]] = relationship(
        back_populates="health_connection"
    )
