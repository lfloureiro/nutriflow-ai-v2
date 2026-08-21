import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.health_connection import HealthConnection
    from app.models.person import Person


class HealthMeasurement(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "health_measurements"
    __table_args__ = (
        CheckConstraint(
            "(observed_at IS NOT NULL AND period_start_at IS NULL AND period_end_at IS NULL) "
            "OR (observed_at IS NULL AND period_start_at IS NOT NULL "
            "AND period_end_at IS NOT NULL AND period_end_at >= period_start_at)",
            name="ck_health_measurements_temporal_shape_valid",
        ),
        CheckConstraint(
            "length(deduplication_key) > 0",
            name="ck_health_measurements_deduplication_key_nonempty",
        ),
        UniqueConstraint(
            "person_id",
            "deduplication_key",
            name="uq_health_measurements_person_deduplication_key",
        ),
        Index(
            "ix_health_measurements_person_metric_observed",
            "person_id",
            "metric",
            "observed_at",
        ),
        Index(
            "ix_health_measurements_person_metric_period",
            "person_id",
            "metric",
            "period_start_at",
        ),
        Index(
            "ix_health_measurements_connection_external",
            "health_connection_id",
            "external_id",
        ),
    )

    person_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("persons.id", ondelete="CASCADE"),
        nullable=False,
    )
    health_connection_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("health_connections.id", ondelete="SET NULL"),
        nullable=True,
    )

    metric: Mapped[str] = mapped_column(String(80), nullable=False)
    value: Mapped[Decimal] = mapped_column(Numeric(16, 4), nullable=False)
    unit: Mapped[str] = mapped_column(String(32), nullable=False)

    observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    period_start_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    period_end_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    provider: Mapped[str] = mapped_column(String(40), nullable=False)
    origin_provider: Mapped[str | None] = mapped_column(String(40), nullable=True)
    source_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    source_device: Mapped[str | None] = mapped_column(String(160), nullable=True)
    source_app: Mapped[str | None] = mapped_column(String(160), nullable=True)

    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    origin_external_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    deduplication_key: Mapped[str] = mapped_column(String(255), nullable=False)

    source_chain: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    provenance_metadata: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    normalization_version: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="1",
    )

    person: Mapped["Person"] = relationship(back_populates="health_measurements")
    health_connection: Mapped["HealthConnection | None"] = relationship(
        back_populates="health_measurements"
    )
