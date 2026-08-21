import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.family import Family


class FoodItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "food_items"
    __table_args__ = (
        CheckConstraint(
            "food_kind IN ('ingredient', 'product', 'dish', 'beverage', 'supplement', 'generic')",
            name="ck_food_items_kind_valid",
        ),
        CheckConstraint(
            "length(catalog_key) > 0",
            name="ck_food_items_catalog_key_nonempty",
        ),
        UniqueConstraint("catalog_key", name="uq_food_items_catalog_key"),
        Index("ix_food_items_kind_name", "food_kind", "name"),
        Index("ix_food_items_family_name", "family_id", "name"),
    )

    family_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("families.id", ondelete="SET NULL"),
        nullable=True,
    )

    catalog_key: Mapped[str] = mapped_column(String(120), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    food_kind: Mapped[str] = mapped_column(String(32), nullable=False, default="ingredient")
    brand: Mapped[str | None] = mapped_column(String(120), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    source: Mapped[str] = mapped_column(String(32), nullable=False, default="user")
    source_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    family: Mapped["Family | None"] = relationship(back_populates="food_items")
    compositions: Mapped[list["FoodCompositionSnapshot"]] = relationship(
        back_populates="food_item",
        cascade="all, delete-orphan",
        order_by=lambda: FoodCompositionSnapshot.effective_at,
    )


class FoodCompositionSnapshot(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "food_composition_snapshots"
    __table_args__ = (
        CheckConstraint(
            "reference_quantity > 0",
            name="ck_food_composition_snapshots_reference_quantity_positive",
        ),
        CheckConstraint(
            "energy_kcal IS NULL OR energy_kcal >= 0",
            name="ck_food_composition_snapshots_energy_nonnegative",
        ),
        UniqueConstraint(
            "food_item_id",
            "data_version",
            name="uq_food_composition_snapshots_item_version",
        ),
        Index(
            "ix_food_composition_snapshots_item_effective_at",
            "food_item_id",
            "effective_at",
        ),
    )

    food_item_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("food_items.id", ondelete="CASCADE"),
        nullable=False,
    )

    reference_quantity: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    reference_unit: Mapped[str] = mapped_column(String(24), nullable=False)
    energy_kcal: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)

    data_version: Mapped[str] = mapped_column(String(64), nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="user")
    source_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    effective_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    food_item: Mapped[FoodItem] = relationship(back_populates="compositions")
    nutrients: Mapped[list["FoodNutrientComponent"]] = relationship(
        back_populates="composition_snapshot",
        cascade="all, delete-orphan",
        order_by=lambda: FoodNutrientComponent.nutrient_key,
    )


class FoodNutrientComponent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "food_nutrient_components"
    __table_args__ = (
        CheckConstraint(
            "value >= 0",
            name="ck_food_nutrient_components_value_nonnegative",
        ),
        UniqueConstraint(
            "composition_snapshot_id",
            "nutrient_key",
            name="uq_food_nutrient_components_snapshot_nutrient",
        ),
        Index("ix_food_nutrient_components_nutrient", "nutrient_key"),
    )

    composition_snapshot_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("food_composition_snapshots.id", ondelete="CASCADE"),
        nullable=False,
    )

    nutrient_key: Mapped[str] = mapped_column(String(120), nullable=False)
    value: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    unit: Mapped[str] = mapped_column(String(24), nullable=False)

    composition_snapshot: Mapped[FoodCompositionSnapshot] = relationship(
        back_populates="nutrients"
    )


class Recipe(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "recipes"
    __table_args__ = (
        CheckConstraint(
            "length(recipe_key) > 0",
            name="ck_recipes_recipe_key_nonempty",
        ),
        CheckConstraint(
            "yield_quantity IS NULL OR yield_quantity > 0",
            name="ck_recipes_yield_quantity_positive",
        ),
        CheckConstraint(
            "(yield_quantity IS NULL AND yield_unit IS NULL) "
            "OR (yield_quantity IS NOT NULL AND yield_unit IS NOT NULL)",
            name="ck_recipes_yield_shape_valid",
        ),
        CheckConstraint(
            "serving_count IS NULL OR serving_count > 0",
            name="ck_recipes_serving_count_positive",
        ),
        UniqueConstraint("recipe_key", name="uq_recipes_recipe_key"),
        Index("ix_recipes_family_name", "family_id", "name"),
    )

    family_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("families.id", ondelete="SET NULL"),
        nullable=True,
    )

    recipe_key: Mapped[str] = mapped_column(String(120), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    yield_quantity: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    yield_unit: Mapped[str | None] = mapped_column(String(24), nullable=True)
    serving_count: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)

    source: Mapped[str] = mapped_column(String(32), nullable=False, default="user")
    source_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    family: Mapped["Family | None"] = relationship(back_populates="recipes")
    ingredients: Mapped[list["RecipeIngredient"]] = relationship(
        back_populates="recipe",
        cascade="all, delete-orphan",
        order_by=lambda: (RecipeIngredient.sort_order, RecipeIngredient.created_at),
    )
    compositions: Mapped[list["RecipeCompositionSnapshot"]] = relationship(
        back_populates="recipe",
        cascade="all, delete-orphan",
        order_by=lambda: RecipeCompositionSnapshot.computed_at,
    )


class RecipeIngredient(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "recipe_ingredients"
    __table_args__ = (
        CheckConstraint(
            "quantity > 0",
            name="ck_recipe_ingredients_quantity_positive",
        ),
        CheckConstraint(
            "sort_order >= 0",
            name="ck_recipe_ingredients_sort_order_nonnegative",
        ),
        Index("ix_recipe_ingredients_recipe_sort", "recipe_id", "sort_order"),
        Index("ix_recipe_ingredients_food_item", "food_item_id"),
    )

    recipe_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("recipes.id", ondelete="CASCADE"),
        nullable=False,
    )
    food_item_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("food_items.id", ondelete="RESTRICT"),
        nullable=False,
    )

    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    unit: Mapped[str] = mapped_column(String(24), nullable=False)
    preparation: Mapped[str | None] = mapped_column(String(160), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    recipe: Mapped[Recipe] = relationship(back_populates="ingredients")
    food_item: Mapped[FoodItem] = relationship()


class RecipeCompositionSnapshot(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "recipe_composition_snapshots"
    __table_args__ = (
        CheckConstraint(
            "reference_quantity > 0",
            name="ck_recipe_composition_snapshots_reference_quantity_positive",
        ),
        CheckConstraint(
            "energy_kcal IS NULL OR energy_kcal >= 0",
            name="ck_recipe_composition_snapshots_energy_nonnegative",
        ),
        UniqueConstraint(
            "recipe_id",
            "composition_version",
            name="uq_recipe_composition_snapshots_recipe_version",
        ),
        Index(
            "ix_recipe_composition_snapshots_recipe_computed_at",
            "recipe_id",
            "computed_at",
        ),
    )

    recipe_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("recipes.id", ondelete="CASCADE"),
        nullable=False,
    )

    reference_quantity: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    reference_unit: Mapped[str] = mapped_column(String(24), nullable=False)
    energy_kcal: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)

    composition_version: Mapped[str] = mapped_column(String(64), nullable=False)
    calculation_version: Mapped[str] = mapped_column(String(64), nullable=False)
    calculation_inputs: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    recipe: Mapped[Recipe] = relationship(back_populates="compositions")
    nutrients: Mapped[list["RecipeNutrientComponent"]] = relationship(
        back_populates="composition_snapshot",
        cascade="all, delete-orphan",
        order_by=lambda: RecipeNutrientComponent.nutrient_key,
    )


class RecipeNutrientComponent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "recipe_nutrient_components"
    __table_args__ = (
        CheckConstraint(
            "value >= 0",
            name="ck_recipe_nutrient_components_value_nonnegative",
        ),
        UniqueConstraint(
            "composition_snapshot_id",
            "nutrient_key",
            name="uq_recipe_nutrient_components_snapshot_nutrient",
        ),
        Index("ix_recipe_nutrient_components_nutrient", "nutrient_key"),
    )

    composition_snapshot_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("recipe_composition_snapshots.id", ondelete="CASCADE"),
        nullable=False,
    )

    nutrient_key: Mapped[str] = mapped_column(String(120), nullable=False)
    value: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    unit: Mapped[str] = mapped_column(String(24), nullable=False)

    composition_snapshot: Mapped[RecipeCompositionSnapshot] = relationship(
        back_populates="nutrients"
    )
