"""add food catalog and recipe composition

Revision ID: f4b8c2d6a1e3
Revises: e1c5b7a9d2f4
Create Date: 2026-08-21 18:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f4b8c2d6a1e3"
down_revision: Union[str, Sequence[str], None] = "e1c5b7a9d2f4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "food_items",
        sa.Column("family_id", sa.Uuid(), nullable=True),
        sa.Column("catalog_key", sa.String(length=120), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("food_kind", sa.String(length=32), nullable=False),
        sa.Column("brand", sa.String(length=120), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("source_reference", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "food_kind IN ('ingredient', 'product', 'dish', 'beverage', 'supplement', 'generic')",
            name="ck_food_items_kind_valid",
        ),
        sa.CheckConstraint(
            "length(catalog_key) > 0",
            name="ck_food_items_catalog_key_nonempty",
        ),
        sa.ForeignKeyConstraint(["family_id"], ["families.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("catalog_key", name="uq_food_items_catalog_key"),
    )
    op.create_index(
        "ix_food_items_kind_name",
        "food_items",
        ["food_kind", "name"],
        unique=False,
    )
    op.create_index(
        "ix_food_items_family_name",
        "food_items",
        ["family_id", "name"],
        unique=False,
    )

    op.create_table(
        "recipes",
        sa.Column("family_id", sa.Uuid(), nullable=True),
        sa.Column("recipe_key", sa.String(length=120), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("yield_quantity", sa.Numeric(precision=14, scale=4), nullable=True),
        sa.Column("yield_unit", sa.String(length=24), nullable=True),
        sa.Column("serving_count", sa.Numeric(precision=8, scale=2), nullable=True),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("source_reference", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "length(recipe_key) > 0",
            name="ck_recipes_recipe_key_nonempty",
        ),
        sa.CheckConstraint(
            "yield_quantity IS NULL OR yield_quantity > 0",
            name="ck_recipes_yield_quantity_positive",
        ),
        sa.CheckConstraint(
            "(yield_quantity IS NULL AND yield_unit IS NULL) "
            "OR (yield_quantity IS NOT NULL AND yield_unit IS NOT NULL)",
            name="ck_recipes_yield_shape_valid",
        ),
        sa.CheckConstraint(
            "serving_count IS NULL OR serving_count > 0",
            name="ck_recipes_serving_count_positive",
        ),
        sa.ForeignKeyConstraint(["family_id"], ["families.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("recipe_key", name="uq_recipes_recipe_key"),
    )
    op.create_index(
        "ix_recipes_family_name",
        "recipes",
        ["family_id", "name"],
        unique=False,
    )

    op.create_table(
        "food_composition_snapshots",
        sa.Column("food_item_id", sa.Uuid(), nullable=False),
        sa.Column("reference_quantity", sa.Numeric(precision=14, scale=4), nullable=False),
        sa.Column("reference_unit", sa.String(length=24), nullable=False),
        sa.Column("energy_kcal", sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column("data_version", sa.String(length=64), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("source_reference", sa.String(length=255), nullable=True),
        sa.Column("effective_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "reference_quantity > 0",
            name="ck_food_composition_snapshots_reference_quantity_positive",
        ),
        sa.CheckConstraint(
            "energy_kcal IS NULL OR energy_kcal >= 0",
            name="ck_food_composition_snapshots_energy_nonnegative",
        ),
        sa.ForeignKeyConstraint(["food_item_id"], ["food_items.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "food_item_id",
            "data_version",
            name="uq_food_composition_snapshots_item_version",
        ),
    )
    op.create_index(
        "ix_food_composition_snapshots_item_effective_at",
        "food_composition_snapshots",
        ["food_item_id", "effective_at"],
        unique=False,
    )

    op.create_table(
        "food_nutrient_components",
        sa.Column("composition_snapshot_id", sa.Uuid(), nullable=False),
        sa.Column("nutrient_key", sa.String(length=120), nullable=False),
        sa.Column("value", sa.Numeric(precision=14, scale=4), nullable=False),
        sa.Column("unit", sa.String(length=24), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "value >= 0",
            name="ck_food_nutrient_components_value_nonnegative",
        ),
        sa.ForeignKeyConstraint(
            ["composition_snapshot_id"],
            ["food_composition_snapshots.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "composition_snapshot_id",
            "nutrient_key",
            name="uq_food_nutrient_components_snapshot_nutrient",
        ),
    )
    op.create_index(
        "ix_food_nutrient_components_nutrient",
        "food_nutrient_components",
        ["nutrient_key"],
        unique=False,
    )

    op.create_table(
        "recipe_ingredients",
        sa.Column("recipe_id", sa.Uuid(), nullable=False),
        sa.Column("food_item_id", sa.Uuid(), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=14, scale=4), nullable=False),
        sa.Column("unit", sa.String(length=24), nullable=False),
        sa.Column("preparation", sa.String(length=160), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "quantity > 0",
            name="ck_recipe_ingredients_quantity_positive",
        ),
        sa.CheckConstraint(
            "sort_order >= 0",
            name="ck_recipe_ingredients_sort_order_nonnegative",
        ),
        sa.ForeignKeyConstraint(["recipe_id"], ["recipes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["food_item_id"], ["food_items.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_recipe_ingredients_recipe_sort",
        "recipe_ingredients",
        ["recipe_id", "sort_order"],
        unique=False,
    )
    op.create_index(
        "ix_recipe_ingredients_food_item",
        "recipe_ingredients",
        ["food_item_id"],
        unique=False,
    )

    op.create_table(
        "recipe_composition_snapshots",
        sa.Column("recipe_id", sa.Uuid(), nullable=False),
        sa.Column("reference_quantity", sa.Numeric(precision=14, scale=4), nullable=False),
        sa.Column("reference_unit", sa.String(length=24), nullable=False),
        sa.Column("energy_kcal", sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column("composition_version", sa.String(length=64), nullable=False),
        sa.Column("calculation_version", sa.String(length=64), nullable=False),
        sa.Column("calculation_inputs", sa.JSON(), nullable=True),
        sa.Column(
            "computed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "reference_quantity > 0",
            name="ck_recipe_composition_snapshots_reference_quantity_positive",
        ),
        sa.CheckConstraint(
            "energy_kcal IS NULL OR energy_kcal >= 0",
            name="ck_recipe_composition_snapshots_energy_nonnegative",
        ),
        sa.ForeignKeyConstraint(["recipe_id"], ["recipes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "recipe_id",
            "composition_version",
            name="uq_recipe_composition_snapshots_recipe_version",
        ),
    )
    op.create_index(
        "ix_recipe_composition_snapshots_recipe_computed_at",
        "recipe_composition_snapshots",
        ["recipe_id", "computed_at"],
        unique=False,
    )

    op.create_table(
        "recipe_nutrient_components",
        sa.Column("composition_snapshot_id", sa.Uuid(), nullable=False),
        sa.Column("nutrient_key", sa.String(length=120), nullable=False),
        sa.Column("value", sa.Numeric(precision=14, scale=4), nullable=False),
        sa.Column("unit", sa.String(length=24), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "value >= 0",
            name="ck_recipe_nutrient_components_value_nonnegative",
        ),
        sa.ForeignKeyConstraint(
            ["composition_snapshot_id"],
            ["recipe_composition_snapshots.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "composition_snapshot_id",
            "nutrient_key",
            name="uq_recipe_nutrient_components_snapshot_nutrient",
        ),
    )
    op.create_index(
        "ix_recipe_nutrient_components_nutrient",
        "recipe_nutrient_components",
        ["nutrient_key"],
        unique=False,
    )

    op.add_column("servings", sa.Column("food_item_id", sa.Uuid(), nullable=True))
    op.add_column("servings", sa.Column("recipe_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_servings_food_item_id_food_items",
        "servings",
        "food_items",
        ["food_item_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_servings_recipe_id_recipes",
        "servings",
        "recipes",
        ["recipe_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_check_constraint(
        "ck_servings_single_catalog_reference",
        "servings",
        "food_item_id IS NULL OR recipe_id IS NULL",
    )
    op.create_index("ix_servings_food_item", "servings", ["food_item_id"], unique=False)
    op.create_index("ix_servings_recipe", "servings", ["recipe_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_servings_recipe", table_name="servings")
    op.drop_index("ix_servings_food_item", table_name="servings")
    op.drop_constraint(
        "ck_servings_single_catalog_reference",
        "servings",
        type_="check",
    )
    op.drop_constraint(
        "fk_servings_recipe_id_recipes",
        "servings",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_servings_food_item_id_food_items",
        "servings",
        type_="foreignkey",
    )
    op.drop_column("servings", "recipe_id")
    op.drop_column("servings", "food_item_id")

    op.drop_index(
        "ix_recipe_nutrient_components_nutrient",
        table_name="recipe_nutrient_components",
    )
    op.drop_table("recipe_nutrient_components")

    op.drop_index(
        "ix_recipe_composition_snapshots_recipe_computed_at",
        table_name="recipe_composition_snapshots",
    )
    op.drop_table("recipe_composition_snapshots")

    op.drop_index("ix_recipe_ingredients_food_item", table_name="recipe_ingredients")
    op.drop_index("ix_recipe_ingredients_recipe_sort", table_name="recipe_ingredients")
    op.drop_table("recipe_ingredients")

    op.drop_index(
        "ix_food_nutrient_components_nutrient",
        table_name="food_nutrient_components",
    )
    op.drop_table("food_nutrient_components")

    op.drop_index(
        "ix_food_composition_snapshots_item_effective_at",
        table_name="food_composition_snapshots",
    )
    op.drop_table("food_composition_snapshots")

    op.drop_index("ix_recipes_family_name", table_name="recipes")
    op.drop_table("recipes")

    op.drop_index("ix_food_items_family_name", table_name="food_items")
    op.drop_index("ix_food_items_kind_name", table_name="food_items")
    op.drop_table("food_items")
