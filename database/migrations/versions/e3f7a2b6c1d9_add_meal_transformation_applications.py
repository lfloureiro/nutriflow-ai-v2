"""add meal transformation applications

Revision ID: e3f7a2b6c1d9
Revises: d2e6f1a9c4b7
Create Date: 2026-09-17
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "e3f7a2b6c1d9"
down_revision: str | Sequence[str] | None = "d2e6f1a9c4b7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "meal_transformation_applications",
        sa.Column("meal_event_id", sa.Uuid(), nullable=False),
        sa.Column("recipe_id", sa.Uuid(), nullable=True),
        sa.Column("source_recipe_composition_snapshot_id", sa.Uuid(), nullable=True),
        sa.Column("recipe_ingredient_id", sa.Uuid(), nullable=True),
        sa.Column("source_food_item_id", sa.Uuid(), nullable=True),
        sa.Column("replacement_food_item_id", sa.Uuid(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("operation_type", sa.String(length=32), nullable=False),
        sa.Column("transformation_kind", sa.String(length=32), nullable=False),
        sa.Column("substitution_group", sa.String(length=64), nullable=False),
        sa.Column("source_food_name", sa.String(length=160), nullable=False),
        sa.Column("source_quantity", sa.Numeric(14, 4), nullable=False),
        sa.Column("source_unit", sa.String(length=24), nullable=False),
        sa.Column("replacement_food_name", sa.String(length=160), nullable=False),
        sa.Column("replacement_quantity", sa.Numeric(14, 4), nullable=False),
        sa.Column("replacement_unit", sa.String(length=24), nullable=False),
        sa.Column("engine_version", sa.String(length=96), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
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
            "operation_type IN ('replace_ingredient')",
            name="ck_meal_transformation_applications_operation_type",
        ),
        sa.CheckConstraint(
            "transformation_kind IN ('plan_adapted', 'preference_variant')",
            name="ck_meal_transformation_applications_kind",
        ),
        sa.CheckConstraint(
            "sort_order >= 0",
            name="ck_meal_transformation_applications_sort_nonnegative",
        ),
        sa.CheckConstraint(
            "source_quantity > 0 AND replacement_quantity > 0",
            name="ck_meal_transformation_applications_quantities_positive",
        ),
        sa.ForeignKeyConstraint(
            ["meal_event_id"],
            ["meal_events.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["recipe_id"],
            ["recipes.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["source_recipe_composition_snapshot_id"],
            ["recipe_composition_snapshots.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["recipe_ingredient_id"],
            ["recipe_ingredients.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["source_food_item_id"],
            ["food_items.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["replacement_food_item_id"],
            ["food_items.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "meal_event_id",
            "sort_order",
            name="uq_meal_transformation_applications_event_sort",
        ),
    )
    op.create_index(
        "ix_meal_transformation_applications_event",
        "meal_transformation_applications",
        ["meal_event_id"],
        unique=False,
    )
    op.create_index(
        "ix_meal_transformation_applications_recipe",
        "meal_transformation_applications",
        ["recipe_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_meal_transformation_applications_recipe",
        table_name="meal_transformation_applications",
    )
    op.drop_index(
        "ix_meal_transformation_applications_event",
        table_name="meal_transformation_applications",
    )
    op.drop_table("meal_transformation_applications")
