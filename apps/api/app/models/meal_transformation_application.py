import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
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
    from app.models.food_catalog import (
        FoodItem,
        Recipe,
        RecipeCompositionSnapshot,
        RecipeIngredient,
    )
    from app.models.meal import MealEvent


class MealTransformationApplication(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "meal_transformation_applications"
    __table_args__ = (
        CheckConstraint(
            "operation_type IN ('replace_ingredient')",
            name="ck_meal_transformation_applications_operation_type",
        ),
        CheckConstraint(
            "transformation_kind IN ('plan_adapted', 'preference_variant')",
            name="ck_meal_transformation_applications_kind",
        ),
        CheckConstraint(
            "sort_order >= 0",
            name="ck_meal_transformation_applications_sort_nonnegative",
        ),
        CheckConstraint(
            "source_quantity > 0 AND replacement_quantity > 0",
            name="ck_meal_transformation_applications_quantities_positive",
        ),
        UniqueConstraint(
            "meal_event_id",
            "sort_order",
            name="uq_meal_transformation_applications_event_sort",
        ),
        Index(
            "ix_meal_transformation_applications_event",
            "meal_event_id",
        ),
        Index(
            "ix_meal_transformation_applications_recipe",
            "recipe_id",
        ),
    )

    meal_event_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("meal_events.id", ondelete="CASCADE"),
        nullable=False,
    )
    recipe_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("recipes.id", ondelete="SET NULL"),
        nullable=True,
    )
    source_recipe_composition_snapshot_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("recipe_composition_snapshots.id", ondelete="SET NULL"),
        nullable=True,
    )
    recipe_ingredient_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("recipe_ingredients.id", ondelete="SET NULL"),
        nullable=True,
    )
    source_food_item_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("food_items.id", ondelete="SET NULL"),
        nullable=True,
    )
    replacement_food_item_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("food_items.id", ondelete="SET NULL"),
        nullable=True,
    )

    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    operation_type: Mapped[str] = mapped_column(String(32), nullable=False)
    transformation_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    substitution_group: Mapped[str] = mapped_column(String(64), nullable=False)

    source_food_name: Mapped[str] = mapped_column(String(160), nullable=False)
    source_quantity: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    source_unit: Mapped[str] = mapped_column(String(24), nullable=False)
    replacement_food_name: Mapped[str] = mapped_column(String(160), nullable=False)
    replacement_quantity: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    replacement_unit: Mapped[str] = mapped_column(String(24), nullable=False)

    engine_version: Mapped[str] = mapped_column(String(96), nullable=False)
    evidence: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    meal_event: Mapped["MealEvent"] = relationship(back_populates="transformation_applications")
    recipe: Mapped["Recipe | None"] = relationship()
    source_recipe_composition_snapshot: Mapped[
        "RecipeCompositionSnapshot | None"
    ] = relationship()
    recipe_ingredient: Mapped["RecipeIngredient | None"] = relationship()
    source_food_item: Mapped["FoodItem | None"] = relationship(
        foreign_keys=[source_food_item_id]
    )
    replacement_food_item: Mapped["FoodItem | None"] = relationship(
        foreign_keys=[replacement_food_item_id]
    )
