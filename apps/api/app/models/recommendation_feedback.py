import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    JSON,
    Boolean,
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
    from app.models.daily_nutrition_state import DailyNutritionState
    from app.models.food_catalog import (
        FoodCompositionSnapshot,
        FoodItem,
        Recipe,
        RecipeCompositionSnapshot,
    )
    from app.models.meal import Serving
    from app.models.person import Person


class MealRecommendationRun(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "meal_recommendation_runs"
    __table_args__ = (
        CheckConstraint(
            "length(engine_version) > 0",
            name="ck_meal_recommendation_runs_engine_version_nonempty",
        ),
        Index(
            "ix_meal_recommendation_runs_person_date",
            "person_id",
            "planning_date",
        ),
    )

    person_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("persons.id", ondelete="CASCADE"),
        nullable=False,
    )
    daily_nutrition_state_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("daily_nutrition_states.id", ondelete="SET NULL"),
        nullable=True,
    )

    planning_date: Mapped[date] = mapped_column(Date, nullable=False)
    meal_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    engine_version: Mapped[str] = mapped_column(String(64), nullable=False)
    context: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)

    person: Mapped["Person"] = relationship(back_populates="meal_recommendation_runs")
    daily_nutrition_state: Mapped["DailyNutritionState | None"] = relationship()
    options: Mapped[list["MealRecommendationOption"]] = relationship(
        back_populates="recommendation_run",
        cascade="all, delete-orphan",
        order_by=lambda: (
            MealRecommendationOption.eligible.desc(),
            MealRecommendationOption.rank,
            MealRecommendationOption.candidate_key,
        ),
    )


class MealRecommendationOption(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "meal_recommendation_options"
    __table_args__ = (
        CheckConstraint(
            "quantity > 0",
            name="ck_meal_recommendation_options_quantity_positive",
        ),
        CheckConstraint(
            "food_item_id IS NULL OR recipe_id IS NULL",
            name="ck_meal_recommendation_options_single_catalog_reference",
        ),
        CheckConstraint(
            "food_composition_snapshot_id IS NULL OR recipe_composition_snapshot_id IS NULL",
            name="ck_meal_recommendation_options_single_composition_reference",
        ),
        CheckConstraint(
            "(eligible AND rank IS NOT NULL AND rank > 0 AND score IS NOT NULL) "
            "OR (NOT eligible AND rank IS NULL AND score IS NULL)",
            name="ck_meal_recommendation_options_evaluation_shape_valid",
        ),
        UniqueConstraint(
            "recommendation_run_id",
            "candidate_kind",
            "candidate_key",
            name="uq_meal_recommendation_options_run_candidate",
        ),
        Index(
            "ix_meal_recommendation_options_run_rank",
            "recommendation_run_id",
            "rank",
        ),
        Index(
            "ix_meal_recommendation_options_candidate",
            "candidate_kind",
            "candidate_key",
        ),
    )

    recommendation_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("meal_recommendation_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    food_item_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("food_items.id", ondelete="SET NULL"),
        nullable=True,
    )
    recipe_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("recipes.id", ondelete="SET NULL"),
        nullable=True,
    )
    food_composition_snapshot_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("food_composition_snapshots.id", ondelete="SET NULL"),
        nullable=True,
    )
    recipe_composition_snapshot_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("recipe_composition_snapshots.id", ondelete="SET NULL"),
        nullable=True,
    )

    candidate_key: Mapped[str] = mapped_column(String(160), nullable=False)
    candidate_name: Mapped[str] = mapped_column(String(160), nullable=False)
    candidate_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    quantity_unit: Mapped[str] = mapped_column(String(24), nullable=False)

    eligible: Mapped[bool] = mapped_column(Boolean, nullable=False)
    rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    score: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    score_breakdown: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    exclusion_reasons: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    explanation: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    candidate_subjects: Mapped[list[dict[str, str]]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    nutrition_snapshot: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)

    recommendation_run: Mapped[MealRecommendationRun] = relationship(back_populates="options")
    food_item: Mapped["FoodItem | None"] = relationship()
    recipe: Mapped["Recipe | None"] = relationship()
    food_composition_snapshot: Mapped["FoodCompositionSnapshot | None"] = relationship()
    recipe_composition_snapshot: Mapped["RecipeCompositionSnapshot | None"] = relationship()
    feedback_events: Mapped[list["MealRecommendationFeedback"]] = relationship(
        back_populates="recommendation_option",
        cascade="all, delete-orphan",
        order_by=lambda: MealRecommendationFeedback.recorded_at,
    )


class MealRecommendationFeedback(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "meal_recommendation_feedback"
    __table_args__ = (
        CheckConstraint(
            "action IN ('accepted', 'rejected', 'modified')",
            name="ck_meal_recommendation_feedback_action_valid",
        ),
        CheckConstraint(
            "length(source) > 0",
            name="ck_meal_recommendation_feedback_source_nonempty",
        ),
        Index(
            "ix_meal_recommendation_feedback_option_recorded_at",
            "recommendation_option_id",
            "recorded_at",
        ),
    )

    recommendation_option_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("meal_recommendation_options.id", ondelete="CASCADE"),
        nullable=False,
    )
    resulting_serving_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("servings.id", ondelete="SET NULL"),
        nullable=True,
    )

    action: Mapped[str] = mapped_column(String(16), nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="user")
    feedback_metadata: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    recommendation_option: Mapped[MealRecommendationOption] = relationship(
        back_populates="feedback_events"
    )
    resulting_serving: Mapped["Serving | None"] = relationship()
