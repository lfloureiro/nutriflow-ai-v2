"""add health measurements

Revision ID: b8e6d4c2a1f9
Revises: f3a9c2d7e1b4
Create Date: 2026-08-21 16:58:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b8e6d4c2a1f9"
down_revision: Union[str, Sequence[str], None] = "f3a9c2d7e1b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "health_measurements",
        sa.Column("person_id", sa.Uuid(), nullable=False),
        sa.Column("health_connection_id", sa.Uuid(), nullable=True),
        sa.Column("metric", sa.String(length=80), nullable=False),
        sa.Column("value", sa.Numeric(precision=16, scale=4), nullable=False),
        sa.Column("unit", sa.String(length=32), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("period_start_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("period_end_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("origin_provider", sa.String(length=40), nullable=True),
        sa.Column("source_kind", sa.String(length=32), nullable=False),
        sa.Column("source_device", sa.String(length=160), nullable=True),
        sa.Column("source_app", sa.String(length=160), nullable=True),
        sa.Column("external_id", sa.String(length=255), nullable=True),
        sa.Column("origin_external_id", sa.String(length=255), nullable=True),
        sa.Column("deduplication_key", sa.String(length=255), nullable=False),
        sa.Column("source_chain", sa.JSON(), nullable=False),
        sa.Column("provenance_metadata", sa.JSON(), nullable=True),
        sa.Column("normalization_version", sa.String(length=64), nullable=False),
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
            "(observed_at IS NOT NULL AND period_start_at IS NULL AND period_end_at IS NULL) "
            "OR (observed_at IS NULL AND period_start_at IS NOT NULL "
            "AND period_end_at IS NOT NULL AND period_end_at >= period_start_at)",
            name="ck_health_measurements_temporal_shape_valid",
        ),
        sa.CheckConstraint(
            "length(deduplication_key) > 0",
            name="ck_health_measurements_deduplication_key_nonempty",
        ),
        sa.ForeignKeyConstraint(
            ["health_connection_id"],
            ["health_connections.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["person_id"], ["persons.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "person_id",
            "deduplication_key",
            name="uq_health_measurements_person_deduplication_key",
        ),
    )
    op.create_index(
        "ix_health_measurements_connection_external",
        "health_measurements",
        ["health_connection_id", "external_id"],
        unique=False,
    )
    op.create_index(
        "ix_health_measurements_person_metric_observed",
        "health_measurements",
        ["person_id", "metric", "observed_at"],
        unique=False,
    )
    op.create_index(
        "ix_health_measurements_person_metric_period",
        "health_measurements",
        ["person_id", "metric", "period_start_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_health_measurements_person_metric_period",
        table_name="health_measurements",
    )
    op.drop_index(
        "ix_health_measurements_person_metric_observed",
        table_name="health_measurements",
    )
    op.drop_index(
        "ix_health_measurements_connection_external",
        table_name="health_measurements",
    )
    op.drop_table("health_measurements")
