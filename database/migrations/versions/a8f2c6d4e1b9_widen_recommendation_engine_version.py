"""widen recommendation engine version

Revision ID: a8f2c6d4e1b9
Revises: d7a1c5e9b3f2
Create Date: 2026-08-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a8f2c6d4e1b9"
down_revision: str | Sequence[str] | None = "d7a1c5e9b3f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "meal_recommendation_runs",
        "engine_version",
        existing_type=sa.String(length=64),
        type_=sa.String(length=160),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "meal_recommendation_runs",
        "engine_version",
        existing_type=sa.String(length=160),
        type_=sa.String(length=64),
        existing_nullable=False,
    )
