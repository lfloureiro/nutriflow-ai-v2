import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
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
    from app.models.family import Family
    from app.models.person import Person


class MealEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "meal_events"
    __table_args__ = (
        CheckConstraint(
            "status IN ('planned', 'prepared', 'served', 'completed', 'cancelled', 'replaced')",
            name="ck_meal_events_status_valid",
        ),
        CheckConstraint(
            "completed_at IS NULL OR served_at IS NULL OR completed_at >= served_at",
            name="ck_meal_events_completion_after_serving",
        ),
        CheckConstraint(
            "replaces_meal_event_id IS NULL OR replaces_meal_event_id <> id",
            name="ck_meal_events_not_self_replacing",
        ),
        Index(
            "ix_meal_events_family_scheduled_at",
            "family_id",
            "scheduled_at",
        ),
        Index(
            "ix_meal_events_family_status",
            "family_id",
            "status",
        ),
    )

    family_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("families.id", ondelete="CASCADE"),
        nullable=False,
    )
    replaces_meal_event_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("meal_events.id", ondelete="SET NULL"),
        nullable=True,
    )

    meal_type: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str | None] = mapped_column(String(160), nullable=True)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False)

    status: Mapped[str] = mapped_column(String(24), nullable=False, default="planned")
    served_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    location: Mapped[str | None] = mapped_column(String(160), nullable=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="user")
    source_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    family: Mapped["Family"] = relationship(back_populates="meal_events")
    participants: Mapped[list["MealParticipant"]] = relationship(
        back_populates="meal_event",
        cascade="all, delete-orphan",
        order_by=lambda: MealParticipant.created_at,
    )
    replaces_meal_event: Mapped["MealEvent | None"] = relationship(
        remote_side="MealEvent.id",
        foreign_keys=[replaces_meal_event_id],
    )


class MealParticipant(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "meal_participants"
    __table_args__ = (
        CheckConstraint(
            "status IN ('planned', 'served', 'consumed', 'partial', 'skipped', 'replaced')",
            name="ck_meal_participants_status_valid",
        ),
        UniqueConstraint(
            "meal_event_id",
            "person_id",
            name="uq_meal_participants_event_person",
        ),
        Index(
            "ix_meal_participants_person_event",
            "person_id",
            "meal_event_id",
        ),
        Index(
            "ix_meal_participants_person_status",
            "person_id",
            "status",
        ),
    )

    meal_event_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("meal_events.id", ondelete="CASCADE"),
        nullable=False,
    )
    person_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("persons.id", ondelete="CASCADE"),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(String(24), nullable=False, default="planned")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    meal_event: Mapped[MealEvent] = relationship(back_populates="participants")
    person: Mapped["Person"] = relationship(back_populates="meal_participations")
    servings: Mapped[list["Serving"]] = relationship(
        back_populates="meal_participant",
        cascade="all, delete-orphan",
        order_by=lambda: Serving.created_at,
    )


class Serving(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "servings"
    __table_args__ = (
        CheckConstraint(
            "status IN ('planned', 'served', 'consumed', 'partial', 'skipped', 'replaced')",
            name="ck_servings_status_valid",
        ),
        CheckConstraint(
            "quantity_planned IS NULL OR quantity_planned >= 0",
            name="ck_servings_quantity_planned_nonnegative",
        ),
        CheckConstraint(
            "quantity_served IS NULL OR quantity_served >= 0",
            name="ck_servings_quantity_served_nonnegative",
        ),
        CheckConstraint(
            "quantity_consumed IS NULL OR quantity_consumed >= 0",
            name="ck_servings_quantity_consumed_nonnegative",
        ),
        CheckConstraint(
            "energy_planned_kcal IS NULL OR energy_planned_kcal >= 0",
            name="ck_servings_energy_planned_nonnegative",
        ),
        CheckConstraint(
            "energy_served_kcal IS NULL OR energy_served_kcal >= 0",
            name="ck_servings_energy_served_nonnegative",
        ),
        CheckConstraint(
            "energy_consumed_kcal IS NULL OR energy_consumed_kcal >= 0",
            name="ck_servings_energy_consumed_nonnegative",
        ),
        CheckConstraint(
            "quantity_consumed IS NULL OR quantity_served IS NULL "
            "OR quantity_consumed <= quantity_served",
            name="ck_servings_consumed_not_above_served",
        ),
        CheckConstraint(
            "(quantity_planned IS NULL AND quantity_served IS NULL AND quantity_consumed IS NULL) "
            "OR quantity_unit IS NOT NULL",
            name="ck_servings_quantity_unit_present",
        ),
        Index(
            "ix_servings_participant_status",
            "meal_participant_id",
            "status",
        ),
        Index(
            "ix_servings_item",
            "item_type",
            "item_key",
        ),
    )

    meal_participant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("meal_participants.id", ondelete="CASCADE"),
        nullable=False,
    )

    item_type: Mapped[str] = mapped_column(String(32), nullable=False, default="dish")
    item_key: Mapped[str | None] = mapped_column(String(120), nullable=True)
    item_name: Mapped[str] = mapped_column(String(160), nullable=False)

    status: Mapped[str] = mapped_column(String(24), nullable=False, default="planned")

    quantity_planned: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    quantity_served: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    quantity_consumed: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    quantity_unit: Mapped[str | None] = mapped_column(String(24), nullable=True)

    energy_planned_kcal: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    energy_served_kcal: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    energy_consumed_kcal: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)

    nutrition_source: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="estimated",
    )
    source_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    meal_participant: Mapped[MealParticipant] = relationship(back_populates="servings")
    nutrition_components: Mapped[list["ServingNutritionComponent"]] = relationship(
        back_populates="serving",
        cascade="all, delete-orphan",
        order_by=lambda: ServingNutritionComponent.nutrient_key,
    )


class ServingNutritionComponent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "serving_nutrition_components"
    __table_args__ = (
        CheckConstraint(
            "planned_value IS NULL OR planned_value >= 0",
            name="ck_serving_nutrition_components_planned_nonnegative",
        ),
        CheckConstraint(
            "served_value IS NULL OR served_value >= 0",
            name="ck_serving_nutrition_components_served_nonnegative",
        ),
        CheckConstraint(
            "consumed_value IS NULL OR consumed_value >= 0",
            name="ck_serving_nutrition_components_consumed_nonnegative",
        ),
        CheckConstraint(
            "planned_value IS NOT NULL OR served_value IS NOT NULL OR consumed_value IS NOT NULL",
            name="ck_serving_nutrition_components_has_value",
        ),
        UniqueConstraint(
            "serving_id",
            "nutrient_key",
            name="uq_serving_nutrition_components_nutrient",
        ),
        Index(
            "ix_serving_nutrition_components_nutrient",
            "nutrient_key",
        ),
    )

    serving_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("servings.id", ondelete="CASCADE"),
        nullable=False,
    )

    nutrient_key: Mapped[str] = mapped_column(String(120), nullable=False)
    planned_value: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    served_value: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    consumed_value: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    unit: Mapped[str] = mapped_column(String(24), nullable=False)

    serving: Mapped[Serving] = relationship(back_populates="nutrition_components")
