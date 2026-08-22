import uuid
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    JSON,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.family import Family
    from app.models.food_catalog import FoodItem, Recipe


class MealCandidatePlanningProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "meal_candidate_planning_profiles"
    __table_args__ = (
        CheckConstraint(
            "candidate_kind IN ('food_item', 'recipe')",
            name="ck_meal_candidate_planning_profiles_kind_valid",
        ),
        CheckConstraint(
            "(candidate_kind = 'food_item' AND food_item_id IS NOT NULL AND recipe_id IS NULL) "
            "OR (candidate_kind = 'recipe' AND food_item_id IS NULL AND recipe_id IS NOT NULL)",
            name="ck_meal_candidate_planning_profiles_catalog_shape",
        ),
        UniqueConstraint(
            "family_id",
            "food_item_id",
            name="uq_meal_candidate_planning_profiles_family_food",
        ),
        UniqueConstraint(
            "family_id",
            "recipe_id",
            name="uq_meal_candidate_planning_profiles_family_recipe",
        ),
        Index(
            "ix_meal_candidate_planning_profiles_family_kind",
            "family_id",
            "candidate_kind",
        ),
    )

    family_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("families.id", ondelete="CASCADE"),
        nullable=False,
    )
    food_item_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("food_items.id", ondelete="CASCADE"),
        nullable=True,
    )
    recipe_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("recipes.id", ondelete="CASCADE"),
        nullable=True,
    )

    candidate_kind: Mapped[str] = mapped_column(String(24), nullable=False)
    planning_category: Mapped[str | None] = mapped_column(String(48), nullable=True)
    primary_protein: Mapped[str | None] = mapped_column(String(48), nullable=True)
    suitable_meal_types: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    auto_plan_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    source: Mapped[str] = mapped_column(String(32), nullable=False, default="derived")
    source_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)

    family: Mapped["Family"] = relationship()
    food_item: Mapped["FoodItem | None"] = relationship()
    recipe: Mapped["Recipe | None"] = relationship()
