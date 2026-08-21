"""add serving nutrition provenance

Revision ID: a2d6e8f1c3b5
Revises: f4b8c2d6a1e3
Create Date: 2026-08-21 18:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a2d6e8f1c3b5"
down_revision: Union[str, Sequence[str], None] = "f4b8c2d6a1e3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "servings",
        sa.Column("food_composition_snapshot_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "servings",
        sa.Column("recipe_composition_snapshot_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "servings",
        sa.Column("nutrition_calculation_version", sa.String(length=64), nullable=True),
    )

    op.create_foreign_key(
        "fk_servings_food_composition_snapshot_id",
        "servings",
        "food_composition_snapshots",
        ["food_composition_snapshot_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_servings_recipe_composition_snapshot_id",
        "servings",
        "recipe_composition_snapshots",
        ["recipe_composition_snapshot_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_check_constraint(
        "ck_servings_single_composition_reference",
        "servings",
        "food_composition_snapshot_id IS NULL OR recipe_composition_snapshot_id IS NULL",
    )
    op.create_index(
        "ix_servings_food_composition",
        "servings",
        ["food_composition_snapshot_id"],
        unique=False,
    )
    op.create_index(
        "ix_servings_recipe_composition",
        "servings",
        ["recipe_composition_snapshot_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_servings_recipe_composition", table_name="servings")
    op.drop_index("ix_servings_food_composition", table_name="servings")
    op.drop_constraint(
        "ck_servings_single_composition_reference",
        "servings",
        type_="check",
    )
    op.drop_constraint(
        "fk_servings_recipe_composition_snapshot_id",
        "servings",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_servings_food_composition_snapshot_id",
        "servings",
        type_="foreignkey",
    )
    op.drop_column("servings", "nutrition_calculation_version")
    op.drop_column("servings", "recipe_composition_snapshot_id")
    op.drop_column("servings", "food_composition_snapshot_id")
