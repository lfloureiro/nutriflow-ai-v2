"""add food transformation profiles

Revision ID: d2e6f1a9c4b7
Revises: c1f4a8d2e6b9
Create Date: 2026-09-16
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "d2e6f1a9c4b7"
down_revision: str | Sequence[str] | None = "c1f4a8d2e6b9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "food_transformation_profiles",
        sa.Column("family_id", sa.Uuid(), nullable=False),
        sa.Column("food_item_id", sa.Uuid(), nullable=False),
        sa.Column("substitution_group", sa.String(length=64), nullable=False),
        sa.Column("typical_quantity", sa.Numeric(14, 4), nullable=True),
        sa.Column("typical_unit", sa.String(length=24), nullable=True),
        sa.Column(
            "auto_transform_enabled",
            sa.Boolean(),
            server_default=sa.true(),
            nullable=False,
        ),
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
        sa.CheckConstraint(
            "length(substitution_group) > 0",
            name="ck_food_transformation_profiles_group_nonempty",
        ),
        sa.CheckConstraint(
            "typical_quantity IS NULL OR typical_quantity > 0",
            name="ck_food_transformation_profiles_quantity_positive",
        ),
        sa.CheckConstraint(
            "(typical_quantity IS NULL AND typical_unit IS NULL) "
            "OR (typical_quantity IS NOT NULL AND typical_unit IS NOT NULL)",
            name="ck_food_transformation_profiles_portion_shape",
        ),
        sa.ForeignKeyConstraint(["family_id"], ["families.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["food_item_id"], ["food_items.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "family_id",
            "food_item_id",
            name="uq_food_transformation_profiles_family_food",
        ),
    )
    op.create_index(
        "ix_food_transformation_profiles_family_group",
        "food_transformation_profiles",
        ["family_id", "substitution_group"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_food_transformation_profiles_family_group",
        table_name="food_transformation_profiles",
    )
    op.drop_table("food_transformation_profiles")
