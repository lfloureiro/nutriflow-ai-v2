"""add pantry stock lots

Revision ID: f6b3d8e1a5c2
Revises: e5a2c7d9f4b1
Create Date: 2026-08-21
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "f6b3d8e1a5c2"
down_revision: str | Sequence[str] | None = "e5a2c7d9f4b1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "pantry_stock_lots",
        sa.Column("family_id", sa.Uuid(), nullable=False),
        sa.Column("food_item_id", sa.Uuid(), nullable=False),
        sa.Column("stock_key", sa.String(length=160), nullable=False),
        sa.Column("quantity_available", sa.Numeric(precision=14, scale=4), nullable=False),
        sa.Column("unit", sa.String(length=24), nullable=False),
        sa.Column("location", sa.String(length=80), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "observed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("is_available", sa.Boolean(), nullable=False),
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
            "length(stock_key) > 0",
            name="ck_pantry_stock_lots_stock_key_nonempty",
        ),
        sa.CheckConstraint(
            "quantity_available > 0",
            name="ck_pantry_stock_lots_quantity_positive",
        ),
        sa.CheckConstraint(
            "length(unit) > 0",
            name="ck_pantry_stock_lots_unit_nonempty",
        ),
        sa.CheckConstraint(
            "length(source) > 0",
            name="ck_pantry_stock_lots_source_nonempty",
        ),
        sa.ForeignKeyConstraint(["family_id"], ["families.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["food_item_id"], ["food_items.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "family_id",
            "stock_key",
            name="uq_pantry_stock_lots_family_stock_key",
        ),
    )
    op.create_index(
        "ix_pantry_stock_lots_family_food",
        "pantry_stock_lots",
        ["family_id", "food_item_id"],
        unique=False,
    )
    op.create_index(
        "ix_pantry_stock_lots_family_expiry",
        "pantry_stock_lots",
        ["family_id", "expires_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_pantry_stock_lots_family_expiry",
        table_name="pantry_stock_lots",
    )
    op.drop_index(
        "ix_pantry_stock_lots_family_food",
        table_name="pantry_stock_lots",
    )
    op.drop_table("pantry_stock_lots")
