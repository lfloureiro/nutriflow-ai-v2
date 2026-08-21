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
    from app.models.nutrition_target import NutritionTarget
    from app.models.person import Person


class DailyNutritionState(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "daily_nutrition_states"
    __table_args__ = (
        CheckConstraint(
            "energy_consumed_kcal >= 0",
            name="ck_daily_nutrition_states_energy_consumed_nonnegative",
        ),
        CheckConstraint(
            "energy_planned_kcal >= 0",
            name="ck_daily_nutrition_states_energy_planned_nonnegative",
        ),
        CheckConstraint(
            "energy_remaining_min_kcal IS NULL OR energy_remaining_max_kcal IS NULL "
            "OR energy_remaining_max_kcal >= energy_remaining_min_kcal",
            name="ck_daily_nutrition_states_energy_remaining_range_valid",
        ),
        CheckConstraint(
            "adherence_score IS NULL OR (adherence_score >= 0 AND adherence_score <= 1)",
            name="ck_daily_nutrition_states_adherence_range",
        ),
        CheckConstraint(
            "confidence_score IS NULL OR (confidence_score >= 0 AND confidence_score <= 1)",
            name="ck_daily_nutrition_states_confidence_range",
        ),
        UniqueConstraint(
            "person_id",
            "state_date",
            "calculation_version",
            name="uq_daily_nutrition_states_person_date_version",
        ),
        Index(
            "ix_daily_nutrition_states_person_date",
            "person_id",
            "state_date",
        ),
    )

    person_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("persons.id", ondelete="CASCADE"),
        nullable=False,
    )
    nutrition_target_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("nutrition_targets.id", ondelete="SET NULL"),
        nullable=True,
    )

    state_date: Mapped[date] = mapped_column(Date, nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False)

    energy_consumed_kcal: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        default=Decimal(0),
    )
    energy_planned_kcal: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        default=Decimal(0),
    )
    energy_remaining_min_kcal: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
    )
    energy_remaining_max_kcal: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
    )

    adherence_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    confidence_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)

    calculation_version: Mapped[str] = mapped_column(String(64), nullable=False)
    calculation_inputs: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    person: Mapped["Person"] = relationship(back_populates="daily_nutrition_states")
    nutrition_target: Mapped["NutritionTarget | None"] = relationship()
    components: Mapped[list["DailyNutritionStateComponent"]] = relationship(
        back_populates="daily_nutrition_state",
        cascade="all, delete-orphan",
        order_by=lambda: (
            DailyNutritionStateComponent.target_type,
            DailyNutritionStateComponent.target_key,
        ),
    )


class DailyNutritionStateComponent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "daily_nutrition_state_components"
    __table_args__ = (
        CheckConstraint(
            "consumed_value IS NULL OR consumed_value >= 0",
            name="ck_daily_nutrition_state_components_consumed_nonnegative",
        ),
        CheckConstraint(
            "planned_value IS NULL OR planned_value >= 0",
            name="ck_daily_nutrition_state_components_planned_nonnegative",
        ),
        CheckConstraint(
            "remaining_min IS NULL OR remaining_max IS NULL OR remaining_max >= remaining_min",
            name="ck_daily_nutrition_state_components_remaining_range_valid",
        ),
        CheckConstraint(
            "consumed_value IS NOT NULL OR planned_value IS NOT NULL "
            "OR remaining_min IS NOT NULL OR remaining_max IS NOT NULL",
            name="ck_daily_nutrition_state_components_has_value",
        ),
        UniqueConstraint(
            "daily_nutrition_state_id",
            "target_type",
            "target_key",
            name="uq_daily_nutrition_state_components_target_key",
        ),
        Index(
            "ix_daily_nutrition_state_components_target",
            "target_type",
            "target_key",
        ),
    )

    daily_nutrition_state_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("daily_nutrition_states.id", ondelete="CASCADE"),
        nullable=False,
    )

    target_type: Mapped[str] = mapped_column(String(32), nullable=False, default="nutrient")
    target_key: Mapped[str] = mapped_column(String(120), nullable=False)
    consumed_value: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    planned_value: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    remaining_min: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    remaining_max: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    unit: Mapped[str] = mapped_column(String(24), nullable=False)

    daily_nutrition_state: Mapped["DailyNutritionState"] = relationship(
        back_populates="components"
    )
