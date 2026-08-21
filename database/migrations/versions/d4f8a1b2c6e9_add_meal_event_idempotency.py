"""add meal event idempotency

Revision ID: d4f8a1b2c6e9
Revises: c3e7f9a1b5d2
Create Date: 2026-08-21
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "d4f8a1b2c6e9"
down_revision: str | Sequence[str] | None = "c3e7f9a1b5d2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "meal_events",
        sa.Column("idempotency_key", sa.String(length=160), nullable=True),
    )
    op.create_check_constraint(
        "ck_meal_events_idempotency_key_nonempty",
        "meal_events",
        "idempotency_key IS NULL OR length(idempotency_key) > 0",
    )
    op.create_unique_constraint(
        "uq_meal_events_family_idempotency_key",
        "meal_events",
        ["family_id", "idempotency_key"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_meal_events_family_idempotency_key",
        "meal_events",
        type_="unique",
    )
    op.drop_constraint(
        "ck_meal_events_idempotency_key_nonempty",
        "meal_events",
        type_="check",
    )
    op.drop_column("meal_events", "idempotency_key")
