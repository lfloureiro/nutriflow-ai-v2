"""add meal candidate availability

Revision ID: e5a2c7d9f4b1
Revises: d4f8a1b2c6e9
Create Date: 2026-08-21
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "e5a2c7d9f4b1"
down_revision: str | Sequence[str] | None = "d4f8a1b2c6e9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "meal_candidate_availability",
        sa.Column("family_id", sa.Uuid(), nullable=False),
        sa.Column("food_item_id", sa.Uuid(), nullable=True),
        sa.Column("recipe_id", sa.Uuid(), nullable=True),
        sa.Column("candidate_kind", sa.String(length=24), nullable=False),
        sa.Column("source_kind", sa.String(length=24), nullable=False),
        sa.Column("source_key", sa.String(length=160), nullable=False),
        sa.Column("location", sa.String(length=160), nullable=True),
        sa.Column("preparation_minutes", sa.Integer(), nullable=True),
        sa.Column("requires_kitchen", sa.Boolean(), nullable=False),
        sa.Column("is_available", sa.Boolean(), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("source_reference", sa.String(length=255), nullable=True),
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
            "candidate_kind IN ('food_item', 'recipe')",
            name="ck_meal_candidate_availability_candidate_kind_valid",
        ),
        sa.CheckConstraint(
            "source_kind IN ('home', 'pantry', 'restaurant', 'delivery', 'store')",
            name="ck_meal_candidate_availability_source_kind_valid",
        ),
        sa.CheckConstraint(
            "length(source_key) > 0",
            name="ck_meal_candidate_availability_source_key_nonempty",
        ),
        sa.CheckConstraint(
            "preparation_minutes IS NULL OR preparation_minutes >= 0",
            name="ck_meal_candidate_availability_preparation_nonnegative",
        ),
        sa.CheckConstraint(
            "(candidate_kind = 'food_item' AND food_item_id IS NOT NULL AND recipe_id IS NULL) "
            "OR (candidate_kind = 'recipe' AND food_item_id IS NULL AND recipe_id IS NOT NULL)",
            name="ck_meal_candidate_availability_catalog_shape_valid",
        ),
        sa.ForeignKeyConstraint(["family_id"], ["families.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["food_item_id"], ["food_items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["recipe_id"], ["recipes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_meal_candidate_availability_family_kind",
        "meal_candidate_availability",
        ["family_id", "source_kind"],
        unique=False,
    )
    op.create_index(
        "ix_meal_candidate_availability_food_item",
        "meal_candidate_availability",
        ["food_item_id"],
        unique=False,
    )
    op.create_index(
        "ix_meal_candidate_availability_recipe",
        "meal_candidate_availability",
        ["recipe_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_meal_candidate_availability_recipe",
        table_name="meal_candidate_availability",
    )
    op.drop_index(
        "ix_meal_candidate_availability_food_item",
        table_name="meal_candidate_availability",
    )
    op.drop_index(
        "ix_meal_candidate_availability_family_kind",
        table_name="meal_candidate_availability",
    )
    op.drop_table("meal_candidate_availability")
