"""add meal menu snapshots

Revision ID: b6d1e4f8a2c9
Revises: a8f2c6d4e1b9
Create Date: 2026-08-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b6d1e4f8a2c9"
down_revision: str | Sequence[str] | None = "a8f2c6d4e1b9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "meal_menu_snapshots",
        sa.Column("family_id", sa.Uuid(), nullable=False),
        sa.Column("provider_key", sa.String(length=120), nullable=False),
        sa.Column("merchant_key", sa.String(length=160), nullable=False),
        sa.Column("merchant_name", sa.String(length=160), nullable=False),
        sa.Column("source_kind", sa.String(length=24), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("observed_local_date", sa.Date(), nullable=False),
        sa.Column("weekday", sa.Integer(), nullable=False),
        sa.Column("item_count", sa.Integer(), nullable=False),
        sa.Column("is_complete", sa.Boolean(), nullable=False),
        sa.Column("query", sa.String(length=160), nullable=True),
        sa.Column("source_reference", sa.String(length=255), nullable=True),
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
            "source_kind IN ('restaurant', 'delivery')",
            name="ck_meal_menu_snapshots_source_kind_valid",
        ),
        sa.CheckConstraint(
            "weekday >= 0 AND weekday <= 6",
            name="ck_meal_menu_snapshots_weekday_valid",
        ),
        sa.CheckConstraint(
            "item_count >= 0",
            name="ck_meal_menu_snapshots_item_count_nonnegative",
        ),
        sa.ForeignKeyConstraint(
            ["family_id"],
            ["families.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_meal_menu_snapshots_family_merchant_date",
        "meal_menu_snapshots",
        ["family_id", "provider_key", "merchant_key", "observed_local_date"],
        unique=False,
    )
    op.create_index(
        "ix_meal_menu_snapshots_family_merchant_weekday",
        "meal_menu_snapshots",
        ["family_id", "provider_key", "merchant_key", "weekday"],
        unique=False,
    )

    op.create_table(
        "meal_menu_snapshot_items",
        sa.Column("snapshot_id", sa.Uuid(), nullable=False),
        sa.Column("food_item_id", sa.Uuid(), nullable=False),
        sa.Column("item_key", sa.String(length=160), nullable=False),
        sa.Column("item_name", sa.String(length=160), nullable=False),
        sa.Column("item_price", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("source_reference", sa.String(length=255), nullable=True),
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
            "item_price >= 0",
            name="ck_meal_menu_snapshot_items_price_nonnegative",
        ),
        sa.CheckConstraint(
            "length(currency) = 3",
            name="ck_meal_menu_snapshot_items_currency_length",
        ),
        sa.ForeignKeyConstraint(
            ["food_item_id"],
            ["food_items.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["snapshot_id"],
            ["meal_menu_snapshots.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "snapshot_id",
            "item_key",
            name="uq_meal_menu_snapshot_items_snapshot_item_key",
        ),
    )
    op.create_index(
        "ix_meal_menu_snapshot_items_food_item",
        "meal_menu_snapshot_items",
        ["food_item_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_meal_menu_snapshot_items_food_item",
        table_name="meal_menu_snapshot_items",
    )
    op.drop_table("meal_menu_snapshot_items")
    op.drop_index(
        "ix_meal_menu_snapshots_family_merchant_weekday",
        table_name="meal_menu_snapshots",
    )
    op.drop_index(
        "ix_meal_menu_snapshots_family_merchant_date",
        table_name="meal_menu_snapshots",
    )
    op.drop_table("meal_menu_snapshots")
