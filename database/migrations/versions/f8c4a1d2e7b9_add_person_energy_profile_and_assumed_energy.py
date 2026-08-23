"""add person energy profile and assumed energy

Revision ID: f8c4a1d2e7b9
Revises: e6b2c9a4f1d7
Create Date: 2026-08-23
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "f8c4a1d2e7b9"
down_revision: str | Sequence[str] | None = "e6b2c9a4f1d7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "person_profiles",
        sa.Column("activity_level", sa.String(length=24), nullable=True),
    )
    op.add_column(
        "person_profiles",
        sa.Column("standard_breakfast_kcal", sa.Numeric(10, 2), nullable=True),
    )
    op.create_check_constraint(
        "ck_person_profiles_activity_level_valid",
        "person_profiles",
        "activity_level IS NULL OR activity_level IN "
        "('sedentary', 'light', 'moderate', 'active', 'very_active')",
    )
    op.create_check_constraint(
        "ck_person_profiles_standard_breakfast_positive",
        "person_profiles",
        "standard_breakfast_kcal IS NULL OR standard_breakfast_kcal > 0",
    )

    op.add_column(
        "daily_nutrition_states",
        sa.Column(
            "energy_assumed_kcal",
            sa.Numeric(10, 2),
            server_default=sa.text("0"),
            nullable=False,
        ),
    )
    op.create_check_constraint(
        "ck_daily_nutrition_states_energy_assumed_nonnegative",
        "daily_nutrition_states",
        "energy_assumed_kcal >= 0",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_daily_nutrition_states_energy_assumed_nonnegative",
        "daily_nutrition_states",
        type_="check",
    )
    op.drop_column("daily_nutrition_states", "energy_assumed_kcal")

    op.drop_constraint(
        "ck_person_profiles_standard_breakfast_positive",
        "person_profiles",
        type_="check",
    )
    op.drop_constraint(
        "ck_person_profiles_activity_level_valid",
        "person_profiles",
        type_="check",
    )
    op.drop_column("person_profiles", "standard_breakfast_kcal")
    op.drop_column("person_profiles", "activity_level")
