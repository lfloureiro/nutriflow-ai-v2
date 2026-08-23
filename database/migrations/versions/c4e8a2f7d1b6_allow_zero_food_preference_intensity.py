"""allow zero food preference intensity

Revision ID: c4e8a2f7d1b6
Revises: b3d9f1a6c2e4
Create Date: 2026-08-23
"""

from collections.abc import Sequence

from alembic import op

revision: str = "c4e8a2f7d1b6"
down_revision: str | Sequence[str] | None = "b3d9f1a6c2e4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        "ck_food_preferences_intensity_range",
        "food_preferences",
        type_="check",
    )
    op.create_check_constraint(
        "ck_food_preferences_intensity_range",
        "food_preferences",
        "intensity >= 0 AND intensity <= 5",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_food_preferences_intensity_range",
        "food_preferences",
        type_="check",
    )
    op.create_check_constraint(
        "ck_food_preferences_intensity_range",
        "food_preferences",
        "intensity >= 1 AND intensity <= 5",
    )
