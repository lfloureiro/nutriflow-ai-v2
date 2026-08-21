import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.person import Person


class DailyHealthState(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "daily_health_states"
    __table_args__ = (
        CheckConstraint(
            "latest_weight_kg IS NULL OR latest_weight_kg > 0",
            name="ck_daily_health_states_weight_positive",
        ),
        CheckConstraint(
            "steps IS NULL OR steps >= 0",
            name="ck_daily_health_states_steps_nonnegative",
        ),
        CheckConstraint(
            "active_energy_kcal IS NULL OR active_energy_kcal >= 0",
            name="ck_daily_health_states_active_energy_nonnegative",
        ),
        CheckConstraint(
            "resting_energy_kcal IS NULL OR resting_energy_kcal >= 0",
            name="ck_daily_health_states_resting_energy_nonnegative",
        ),
        CheckConstraint(
            "estimated_expenditure_kcal IS NULL OR estimated_expenditure_kcal >= 0",
            name="ck_daily_health_states_expenditure_nonnegative",
        ),
        CheckConstraint(
            "sleep_duration_minutes IS NULL OR sleep_duration_minutes >= 0",
            name="ck_daily_health_states_sleep_nonnegative",
        ),
        CheckConstraint(
            "resting_heart_rate_bpm IS NULL OR resting_heart_rate_bpm > 0",
            name="ck_daily_health_states_resting_hr_positive",
        ),
        CheckConstraint(
            "hrv_ms IS NULL OR hrv_ms >= 0",
            name="ck_daily_health_states_hrv_nonnegative",
        ),
        CheckConstraint(
            "training_load IS NULL OR training_load >= 0",
            name="ck_daily_health_states_training_load_nonnegative",
        ),
        CheckConstraint(
            "confidence_score IS NULL OR (confidence_score >= 0 AND confidence_score <= 1)",
            name="ck_daily_health_states_confidence_range",
        ),
        CheckConstraint(
            "source_window_start_at IS NULL OR source_window_end_at IS NULL "
            "OR source_window_end_at >= source_window_start_at",
            name="ck_daily_health_states_source_window_valid",
        ),
        UniqueConstraint(
            "person_id",
            "state_date",
            "calculation_version",
            name="uq_daily_health_states_person_date_version",
        ),
        Index(
            "ix_daily_health_states_person_date",
            "person_id",
            "state_date",
        ),
    )

    person_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("persons.id", ondelete="CASCADE"),
        nullable=False,
    )

    state_date: Mapped[date] = mapped_column(Date, nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False)

    latest_weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(8, 3), nullable=True)
    weight_trend_7d_kg: Mapped[Decimal | None] = mapped_column(Numeric(8, 3), nullable=True)
    weight_trend_28d_kg: Mapped[Decimal | None] = mapped_column(Numeric(8, 3), nullable=True)

    steps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    active_energy_kcal: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    resting_energy_kcal: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    estimated_expenditure_kcal: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
    )

    sleep_duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    resting_heart_rate_bpm: Mapped[Decimal | None] = mapped_column(
        Numeric(8, 2),
        nullable=True,
    )
    hrv_ms: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    training_load: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)

    confidence_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    calculation_version: Mapped[str] = mapped_column(String(64), nullable=False)
    calculation_inputs: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)

    source_window_start_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    source_window_end_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    person: Mapped["Person"] = relationship(back_populates="daily_health_states")
