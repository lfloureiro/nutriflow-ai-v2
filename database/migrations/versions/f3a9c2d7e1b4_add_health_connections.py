"""add health connections

Revision ID: f3a9c2d7e1b4
Revises: c7f4e2a9b1d3
Create Date: 2026-08-21 16:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f3a9c2d7e1b4"
down_revision: Union[str, Sequence[str], None] = "c7f4e2a9b1d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "health_connections",
        sa.Column("person_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("connection_key", sa.String(length=120), nullable=False),
        sa.Column("connection_kind", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("permissions", sa.JSON(), nullable=False),
        sa.Column("provider_account_id", sa.String(length=255), nullable=True),
        sa.Column("credential_reference", sa.String(length=255), nullable=True),
        sa.Column("provider_metadata", sa.JSON(), nullable=True),
        sa.Column("sync_cursor", sa.Text(), nullable=True),
        sa.Column("last_sync_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_successful_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
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
            "status IN ('pending', 'active', 'paused', 'error', 'revoked')",
            name="ck_health_connections_status_valid",
        ),
        sa.CheckConstraint(
            "revoked_at IS NULL OR status = 'revoked'",
            name="ck_health_connections_revoked_status_valid",
        ),
        sa.ForeignKeyConstraint(["person_id"], ["persons.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "person_id",
            "provider",
            "connection_key",
            name="uq_health_connections_person_provider_key",
        ),
    )
    op.create_index(
        "ix_health_connections_person_provider_status",
        "health_connections",
        ["person_id", "provider", "status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_health_connections_person_provider_status",
        table_name="health_connections",
    )
    op.drop_table("health_connections")
