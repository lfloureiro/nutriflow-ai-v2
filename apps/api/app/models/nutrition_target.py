import uuid
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.person import Person


class NutritionTarget(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "nutrition_targets"
    __table_args__ = (
        CheckConstraint(
            "estimated_bmr_kcal IS NULL OR estimated_bmr_kcal > 0",
            name="ck_nutrition_targets_bmr_positive",
        ),
        CheckConstraint(
            "estimated_tdee_kcal IS NULL OR estimated_tdee_kcal > 0",
            name="ck_nutrition_targets_tdee_positive",
        ),
        CheckConstraint(
            "energy_min_kcal IS NULL OR energy_min_kcal > 0",
            name="ck_nutrition_targets_energy_min_positive",
        ),
        CheckConstraint(
            "energy_max_kcal IS NULL OR energy_max_kcal > 0",
            name="ck_nutrition_targets_energy_max_positive",
        ),
        CheckConstraint(
            "energy_min_kcal IS NULL OR energy_max_kcal IS NULL "
            "OR energy_max_kcal >= energy_min_kcal",
            name="ck_nutrition_targets_energy_range_valid",
        ),
        CheckConstraint(
            "valid_until IS NULL OR valid_until >= valid_from",
            name="ck_nutrition_targets_validity_range_valid",
        ),
        Index(
            "ix_nutrition_targets_person_valid_from",
            "person_id",
            "valid_from",
        ),
        Index(
            "ix_nutrition_targets_person_status",
            "person_id",
            "status",
        ),
    )

    person_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("persons.id", ondelete="CASCADE"),
        nullable=False,
    )
    nutrition_goal_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("nutrition_goals.id", ondelete="SET NULL"),
        nullable=True,
    )

    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)

    estimated_bmr_kcal: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    bmr_method: Mapped[str | None] = mapped_column(String(80), nullable=True)
    estimated_tdee_kcal: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    tdee_method: Mapped[str | None] = mapped_column(String(80), nullable=True)

    energy_min_kcal: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    energy_max_kcal: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)

    calculation_version: Mapped[str] = mapped_column(String(64), nullable=False)
    calculation_inputs: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)

    status: Mapped[str] = mapped_column(String(24), nullable=False, default="active")
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="system")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    person: Mapped["Person"] = relationship(back_populates="nutrition_targets")
    components: Mapped[list["NutritionTargetComponent"]] = relationship(
        back_populates="nutrition_target",
        cascade="all, delete-orphan",
        order_by=lambda: (
            NutritionTargetComponent.target_type,
            NutritionTargetComponent.target_key,
        ),
    )


class NutritionTargetComponent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "nutrition_target_components"
    __table_args__ = (
        CheckConstraint(
            "value_min IS NULL OR value_min >= 0",
            name="ck_nutrition_target_components_value_min_nonnegative",
        ),
        CheckConstraint(
            "value_max IS NULL OR value_max >= 0",
            name="ck_nutrition_target_components_value_max_nonnegative",
        ),
        CheckConstraint(
            "value_target IS NULL OR value_target >= 0",
            name="ck_nutrition_target_components_value_target_nonnegative",
        ),
        CheckConstraint(
            "value_min IS NULL OR value_max IS NULL OR value_max >= value_min",
            name="ck_nutrition_target_components_value_range_valid",
        ),
        CheckConstraint(
            "value_target IS NULL OR value_min IS NULL OR value_target >= value_min",
            name="ck_nutrition_target_components_target_above_min",
        ),
        CheckConstraint(
            "value_target IS NULL OR value_max IS NULL OR value_target <= value_max",
            name="ck_nutrition_target_components_target_below_max",
        ),
        CheckConstraint(
            "value_min IS NOT NULL OR value_max IS NOT NULL OR value_target IS NOT NULL",
            name="ck_nutrition_target_components_has_value",
        ),
        UniqueConstraint(
            "nutrition_target_id",
            "target_type",
            "target_key",
            name="uq_nutrition_target_components_target_key",
        ),
        Index(
            "ix_nutrition_target_components_target",
            "target_type",
            "target_key",
        ),
    )

    nutrition_target_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("nutrition_targets.id", ondelete="CASCADE"),
        nullable=False,
    )

    target_type: Mapped[str] = mapped_column(String(32), nullable=False, default="nutrient")
    target_key: Mapped[str] = mapped_column(String(120), nullable=False)
    value_min: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    value_max: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    value_target: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    unit: Mapped[str] = mapped_column(String(24), nullable=False)

    nutrition_target: Mapped["NutritionTarget"] = relationship(back_populates="components")
