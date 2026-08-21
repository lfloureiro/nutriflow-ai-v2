import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.person import Person


class AnthropometricMeasurement(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "anthropometric_measurements"

    __table_args__ = (
        CheckConstraint(
            "value > 0",
            name="ck_anthropometric_measurements_value_positive",
        ),
        Index(
            "ix_anthropometric_person_metric_measured_at",
            "person_id",
            "metric",
            "measured_at",
        ),
    )

    person_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("persons.id", ondelete="CASCADE"),
        nullable=False,
    )

    metric: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
    )

    value: Mapped[Decimal] = mapped_column(
        Numeric(14, 4),
        nullable=False,
    )

    unit: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
    )

    measured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    source: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="manual",
    )

    provider: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    source_device: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True,
    )

    external_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    person: Mapped["Person"] = relationship(
        back_populates="anthropometric_measurements"
    )
