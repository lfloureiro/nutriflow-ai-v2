"""add catalogue meal suitability

Revision ID: d7a1c5e9b3f2
Revises: c4e8a2f7d1b6
Create Date: 2026-08-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d7a1c5e9b3f2"
down_revision: str | Sequence[str] | None = "c4e8a2f7d1b6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


MAIN_MEAL_TYPES = '["lunch", "dinner"]'
BREAKFAST_MEAL_TYPES = '["breakfast"]'
SNACK_MEAL_TYPES = '["snack"]'


def upgrade() -> None:
    op.add_column(
        "food_items",
        sa.Column("suitable_meal_types", postgresql.JSON(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "recipes",
        sa.Column("suitable_meal_types", postgresql.JSON(astext_type=sa.Text()), nullable=True),
    )

    op.execute(
        sa.text(
            "UPDATE food_items SET suitable_meal_types = CAST(:types AS json) "
            "WHERE food_kind = 'dish' AND suitable_meal_types IS NULL"
        ).bindparams(types=MAIN_MEAL_TYPES)
    )
    op.execute(
        sa.text(
            "UPDATE recipes SET suitable_meal_types = CAST(:types AS json) "
            "WHERE suitable_meal_types IS NULL"
        ).bindparams(types=MAIN_MEAL_TYPES)
    )
    op.execute(
        sa.text(
            "UPDATE recipes SET suitable_meal_types = CAST(:types AS json) "
            "WHERE source = 'development-breakfast'"
        ).bindparams(types=BREAKFAST_MEAL_TYPES)
    )
    op.execute(
        sa.text(
            "UPDATE recipes SET suitable_meal_types = CAST(:types AS json) "
            "WHERE source = 'development-snack'"
        ).bindparams(types=SNACK_MEAL_TYPES)
    )


def downgrade() -> None:
    op.drop_column("recipes", "suitable_meal_types")
    op.drop_column("food_items", "suitable_meal_types")
