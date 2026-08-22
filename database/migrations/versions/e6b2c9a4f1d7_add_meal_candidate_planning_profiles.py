"""add meal candidate planning profiles

Revision ID: e6b2c9a4f1d7
Revises: d4f1a7c2e9b3
Create Date: 2026-08-22
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "e6b2c9a4f1d7"
down_revision: str | Sequence[str] | None = "d4f1a7c2e9b3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "meal_candidate_planning_profiles",
        sa.Column("family_id", sa.Uuid(), nullable=False),
        sa.Column("food_item_id", sa.Uuid(), nullable=True),
        sa.Column("recipe_id", sa.Uuid(), nullable=True),
        sa.Column("candidate_kind", sa.String(length=24), nullable=False),
        sa.Column("planning_category", sa.String(length=48), nullable=True),
        sa.Column("primary_protein", sa.String(length=48), nullable=True),
        sa.Column("suitable_meal_types", sa.JSON(), nullable=True),
        sa.Column(
            "auto_plan_enabled",
            sa.Boolean(),
            server_default=sa.true(),
            nullable=False,
        ),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("source_reference", sa.String(length=255), nullable=True),
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
            name="ck_meal_candidate_planning_profiles_kind_valid",
        ),
        sa.CheckConstraint(
            "(candidate_kind = 'food_item' AND food_item_id IS NOT NULL AND recipe_id IS NULL) "
            "OR (candidate_kind = 'recipe' AND food_item_id IS NULL AND recipe_id IS NOT NULL)",
            name="ck_meal_candidate_planning_profiles_catalog_shape",
        ),
        sa.ForeignKeyConstraint(["family_id"], ["families.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["food_item_id"], ["food_items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["recipe_id"], ["recipes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "family_id",
            "food_item_id",
            name="uq_meal_candidate_planning_profiles_family_food",
        ),
        sa.UniqueConstraint(
            "family_id",
            "recipe_id",
            name="uq_meal_candidate_planning_profiles_family_recipe",
        ),
    )
    op.create_index(
        "ix_meal_candidate_planning_profiles_family_kind",
        "meal_candidate_planning_profiles",
        ["family_id", "candidate_kind"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_meal_candidate_planning_profiles_family_kind",
        table_name="meal_candidate_planning_profiles",
    )
    op.drop_table("meal_candidate_planning_profiles")
