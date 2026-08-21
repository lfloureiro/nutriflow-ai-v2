import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.family import Family
    from app.models.food_catalog import FoodItem, Recipe


AVAILABILITY_KINDS = frozenset({"home", "pantry", "restaurant", "delivery", "store"})


class MealCandidateAvailability(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "meal_candidate_availability"
    __table_args__ = (
        CheckConstraint(
            "candidate_kind IN ('food_item', 'recipe')",
            name="ck_meal_candidate_availability_candidate_kind_valid",
        ),
        CheckConstraint(
            "source_kind IN ('home', 'pantry', 'restaurant', 'delivery', 'store')",
            name="ck_meal_candidate_availability_source_kind_valid",
        ),
        CheckConstraint(
            "length(source_key) > 0",
            name="ck_meal_candidate_availability_source_key_nonempty",
        ),
        CheckConstraint(
            "preparation_minutes IS NULL OR preparation_minutes >= 0",
            name="ck_meal_candidate_availability_preparation_nonnegative",
        ),
        CheckConstraint(
            "(candidate_kind = 'food_item' AND food_item_id IS NOT NULL AND recipe_id IS NULL) "
            "OR (candidate_kind = 'recipe' AND food_item_id IS NULL AND recipe_id IS NOT NULL)",
            name="ck_meal_candidate_availability_catalog_shape_valid",
        ),
        Index(
            "ix_meal_candidate_availability_family_kind",
            "family_id",
            "source_kind",
        ),
        Index(
            "ix_meal_candidate_availability_food_item",
            "food_item_id",
        ),
        Index(
            "ix_meal_candidate_availability_recipe",
            "recipe_id",
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
    source_kind: Mapped[str] = mapped_column(String(24), nullable=False)
    source_key: Mapped[str] = mapped_column(String(160), nullable=False)
    location: Mapped[str | None] = mapped_column(String(160), nullable=True)
    preparation_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    requires_kitchen: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    source: Mapped[str] = mapped_column(String(32), nullable=False, default="user")
    source_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    family: Mapped["Family"] = relationship()
    food_item: Mapped["FoodItem | None"] = relationship()
    recipe: Mapped["Recipe | None"] = relationship()
