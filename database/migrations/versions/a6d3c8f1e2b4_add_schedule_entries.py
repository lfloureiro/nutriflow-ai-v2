"""add schedule entries

Revision ID: a6d3c8f1e2b4
Revises: e4c1a2d9f6b7
Create Date: 2026-08-21 16:04:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a6d3c8f1e2b4"
down_revision: Union[str, Sequence[str], None] = "e4c1a2d9f6b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "schedule_entries",
        sa.Column("person_id", sa.Uuid(), nullable=False),
        sa.Column("entry_type", sa.String(length=16), nullable=False),
        sa.Column("event_type", sa.String(length=40), nullable=False),
        sa.Column("availability_effect", sa.String(length=16), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("local_start_time", sa.Time(), nullable=True),
        sa.Column("local_end_time", sa.Time(), nullable=True),
        sa.Column("recurrence_rule", sa.Text(), nullable=True),
        sa.Column("valid_from", sa.Date(), nullable=True),
        sa.Column("valid_until", sa.Date(), nullable=True),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.Column("flexibility_minutes", sa.Integer(), nullable=False),
        sa.Column("location", sa.String(length=255), nullable=True),
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
            "entry_type IN ('recurring', 'one_off')",
            name="ck_schedule_entries_entry_type_valid",
        ),
        sa.CheckConstraint(
            "availability_effect IN ('neutral', 'available', 'unavailable', 'preferred')",
            name="ck_schedule_entries_availability_effect_valid",
        ),
        sa.CheckConstraint(
            "flexibility_minutes >= 0",
            name="ck_schedule_entries_flexibility_nonnegative",
        ),
        sa.CheckConstraint(
            "starts_at IS NULL OR ends_at IS NULL OR ends_at > starts_at",
            name="ck_schedule_entries_one_off_time_range_valid",
        ),
        sa.CheckConstraint(
            "valid_from IS NULL OR valid_until IS NULL OR valid_until >= valid_from",
            name="ck_schedule_entries_validity_range_valid",
        ),
        sa.CheckConstraint(
            "(entry_type = 'one_off' "
            "AND starts_at IS NOT NULL "
            "AND ends_at IS NOT NULL "
            "AND local_start_time IS NULL "
            "AND local_end_time IS NULL "
            "AND recurrence_rule IS NULL "
            "AND valid_from IS NULL "
            "AND valid_until IS NULL) "
            "OR "
            "(entry_type = 'recurring' "
            "AND starts_at IS NULL "
            "AND ends_at IS NULL "
            "AND local_start_time IS NOT NULL "
            "AND local_end_time IS NOT NULL "
            "AND recurrence_rule IS NOT NULL "
            "AND valid_from IS NOT NULL)",
            name="ck_schedule_entries_entry_shape_valid",
        ),
        sa.ForeignKeyConstraint(["person_id"], ["persons.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_schedule_entries_person_type_event",
        "schedule_entries",
        ["person_id", "entry_type", "event_type"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ix_schedule_entries_person_type_event",
        table_name="schedule_entries",
    )
    op.drop_table("schedule_entries")
