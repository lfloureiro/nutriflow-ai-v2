"""add durable shopping lists

Revision ID: d4f1a7c2e9b3
Revises: a7c4e9f2b6d1
Create Date: 2026-08-22
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "d4f1a7c2e9b3"
down_revision: str | Sequence[str] | None = "a7c4e9f2b6d1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "shopping_lists",
        sa.Column("family_id", sa.Uuid(), nullable=False),
        sa.Column("list_key", sa.String(length=160), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("planning_start", sa.Date(), nullable=True),
        sa.Column("planning_end", sa.Date(), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source", sa.String(length=32), nullable=False),
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
        sa.CheckConstraint("length(list_key) > 0", name="ck_shopping_lists_key_nonempty"),
        sa.CheckConstraint(
            "status IN ('active', 'archived')",
            name="ck_shopping_lists_status_valid",
        ),
        sa.CheckConstraint("length(source) > 0", name="ck_shopping_lists_source_nonempty"),
        sa.ForeignKeyConstraint(["family_id"], ["families.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("family_id", "list_key", name="uq_shopping_lists_family_key"),
    )
    op.create_index(
        "ix_shopping_lists_family_status",
        "shopping_lists",
        ["family_id", "status"],
        unique=False,
    )

    op.create_table(
        "shopping_list_items",
        sa.Column("shopping_list_id", sa.Uuid(), nullable=False),
        sa.Column("food_item_id", sa.Uuid(), nullable=True),
        sa.Column("item_key", sa.String(length=180), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=14, scale=4), nullable=True),
        sa.Column("unit", sa.String(length=24), nullable=True),
        sa.Column("item_source", sa.String(length=24), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
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
            "length(item_key) > 0",
            name="ck_shopping_list_items_key_nonempty",
        ),
        sa.CheckConstraint(
            "length(name) > 0",
            name="ck_shopping_list_items_name_nonempty",
        ),
        sa.CheckConstraint(
            "item_source IN ('automatic', 'manual')",
            name="ck_shopping_list_items_source_valid",
        ),
        sa.CheckConstraint(
            "status IN ('needed', 'purchased')",
            name="ck_shopping_list_items_status_valid",
        ),
        sa.CheckConstraint(
            "(quantity IS NULL AND unit IS NULL) OR "
            "(quantity > 0 AND unit IS NOT NULL AND length(unit) > 0)",
            name="ck_shopping_list_items_quantity_unit_shape",
        ),
        sa.CheckConstraint(
            "sort_order >= 0",
            name="ck_shopping_list_items_sort_nonnegative",
        ),
        sa.ForeignKeyConstraint(["food_item_id"], ["food_items.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["shopping_list_id"],
            ["shopping_lists.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "shopping_list_id",
            "item_key",
            name="uq_shopping_list_items_list_key",
        ),
    )
    op.create_index(
        "ix_shopping_list_items_list_status",
        "shopping_list_items",
        ["shopping_list_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_shopping_list_items_food",
        "shopping_list_items",
        ["food_item_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_shopping_list_items_food", table_name="shopping_list_items")
    op.drop_index("ix_shopping_list_items_list_status", table_name="shopping_list_items")
    op.drop_table("shopping_list_items")
    op.drop_index("ix_shopping_lists_family_status", table_name="shopping_lists")
    op.drop_table("shopping_lists")
