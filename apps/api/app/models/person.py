import uuid
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.anthropometric_measurement import AnthropometricMeasurement
from app.models.daily_health_state import DailyHealthState
from app.models.daily_nutrition_state import DailyNutritionState
from app.models.food_adverse_reaction import FoodAdverseReaction
from app.models.food_preference import FoodPreference
from app.models.health_connection import HealthConnection
from app.models.health_measurement import HealthMeasurement
from app.models.meal import MealParticipant
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.nutrition_constraint import NutritionConstraint
from app.models.nutrition_goal import NutritionGoal
from app.models.nutrition_target import NutritionTarget
from app.models.person_profile import PersonProfile
from app.models.recommendation_feedback import MealRecommendationRun
from app.models.schedule_entry import ScheduleEntry

if TYPE_CHECKING:
    from app.models.family import Family


class Person(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "persons"

    family_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("families.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    preferred_locale: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="pt-PT",
    )

    timezone: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="Europe/Lisbon",
    )

    family: Mapped["Family"] = relationship(back_populates="persons")

    profile: Mapped[PersonProfile | None] = relationship(
        back_populates="person",
        cascade="all, delete-orphan",
        single_parent=True,
        uselist=False,
    )

    anthropometric_measurements: Mapped[list[AnthropometricMeasurement]] = relationship(
        back_populates="person",
        cascade="all, delete-orphan",
        order_by=AnthropometricMeasurement.measured_at,
    )

    nutrition_goals: Mapped[list[NutritionGoal]] = relationship(
        back_populates="person",
        cascade="all, delete-orphan",
        order_by=NutritionGoal.start_date,
    )

    nutrition_constraints: Mapped[list[NutritionConstraint]] = relationship(
        back_populates="person",
        cascade="all, delete-orphan",
        order_by=NutritionConstraint.created_at,
    )

    food_preferences: Mapped[list[FoodPreference]] = relationship(
        back_populates="person",
        cascade="all, delete-orphan",
        order_by=FoodPreference.created_at,
    )

    food_adverse_reactions: Mapped[list[FoodAdverseReaction]] = relationship(
        back_populates="person",
        cascade="all, delete-orphan",
        order_by=FoodAdverseReaction.created_at,
    )

    schedule_entries: Mapped[list[ScheduleEntry]] = relationship(
        back_populates="person",
        cascade="all, delete-orphan",
        order_by=ScheduleEntry.created_at,
    )

    nutrition_targets: Mapped[list[NutritionTarget]] = relationship(
        back_populates="person",
        cascade="all, delete-orphan",
        order_by=NutritionTarget.valid_from,
    )

    health_connections: Mapped[list[HealthConnection]] = relationship(
        back_populates="person",
        cascade="all, delete-orphan",
        order_by=HealthConnection.created_at,
    )

    health_measurements: Mapped[list[HealthMeasurement]] = relationship(
        back_populates="person",
        cascade="all, delete-orphan",
        order_by=HealthMeasurement.created_at,
    )

    daily_health_states: Mapped[list[DailyHealthState]] = relationship(
        back_populates="person",
        cascade="all, delete-orphan",
        order_by=lambda: (DailyHealthState.state_date, DailyHealthState.calculation_version),
    )

    daily_nutrition_states: Mapped[list[DailyNutritionState]] = relationship(
        back_populates="person",
        cascade="all, delete-orphan",
        order_by=lambda: (
            DailyNutritionState.state_date,
            DailyNutritionState.calculation_version,
        ),
    )

    meal_participations: Mapped[list[MealParticipant]] = relationship(
        back_populates="person",
        cascade="all, delete-orphan",
        order_by=MealParticipant.created_at,
    )

    meal_recommendation_runs: Mapped[list[MealRecommendationRun]] = relationship(
        back_populates="person",
        cascade="all, delete-orphan",
        order_by=lambda: (MealRecommendationRun.planning_date, MealRecommendationRun.created_at),
    )
