"""add commercial availability context

Revision ID: a7c4e9f2b6d1
Revises: f6b3d8e1a5c2
Create Date: 2026-08-22
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "a7c4e9f2b6d1"
down_revision: str | Sequence[str] | None = "f6b3d8e1a5c2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "meal_source_opening_windows",
        sa.Column("availability_id", sa.Uuid(), nullable=False),
        sa.Column("weekday", sa.Integer(), nullable=False),
        sa.Column("local_start_time", sa.Time(), nullable=False),
        sa.Column("local_end_time", sa.Time(), nullable=False),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.Column("valid_from", sa.Date(), nullable=True),
        sa.Column("valid_until", sa.Date(), nullable=True),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("source_reference", sa.String(length=255), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=True),
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
            "weekday >= 0 AND weekday <= 6",
            name="ck_meal_source_opening_windows_weekday_valid",
        ),
        sa.CheckConstraint(
            "length(timezone) > 0",
            name="ck_meal_source_opening_windows_timezone_nonempty",
        ),
        sa.CheckConstraint(
            "valid_until IS NULL OR valid_from IS NULL OR valid_until >= valid_from",
            name="ck_meal_source_opening_windows_valid_range",
        ),
        sa.ForeignKeyConstraint(
            ["availability_id"],
            ["meal_candidate_availability.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_meal_source_opening_windows_availability_weekday",
        "meal_source_opening_windows",
        ["availability_id", "weekday"],
        unique=False,
    )

    op.create_table(
        "meal_commercial_offers",
        sa.Column("family_id", sa.Uuid(), nullable=False),
        sa.Column("availability_id", sa.Uuid(), nullable=False),
        sa.Column("offer_key", sa.String(length=160), nullable=False),
        sa.Column("provider_key", sa.String(length=120), nullable=False),
        sa.Column("provider_name", sa.String(length=160), nullable=True),
        sa.Column("item_price", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("delivery_fee", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("minimum_order", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("is_available", sa.Boolean(), nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
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
            "length(offer_key) > 0",
            name="ck_meal_commercial_offers_offer_key_nonempty",
        ),
        sa.CheckConstraint(
            "length(provider_key) > 0",
            name="ck_meal_commercial_offers_provider_key_nonempty",
        ),
        sa.CheckConstraint(
            "length(currency) = 3",
            name="ck_meal_commercial_offers_currency_length",
        ),
        sa.CheckConstraint(
            "item_price >= 0",
            name="ck_meal_commercial_offers_item_price_nonnegative",
        ),
        sa.CheckConstraint(
            "delivery_fee IS NULL OR delivery_fee >= 0",
            name="ck_meal_commercial_offers_delivery_fee_nonnegative",
        ),
        sa.CheckConstraint(
            "minimum_order IS NULL OR minimum_order >= 0",
            name="ck_meal_commercial_offers_minimum_order_nonnegative",
        ),
        sa.CheckConstraint(
            "valid_until IS NULL OR valid_from IS NULL OR valid_until > valid_from",
            name="ck_meal_commercial_offers_valid_range",
        ),
        sa.ForeignKeyConstraint(["family_id"], ["families.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["availability_id"],
            ["meal_candidate_availability.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "family_id",
            "offer_key",
            name="uq_meal_commercial_offers_family_offer_key",
        ),
    )
    op.create_index(
        "ix_meal_commercial_offers_availability",
        "meal_commercial_offers",
        ["availability_id"],
        unique=False,
    )
    op.create_index(
        "ix_meal_commercial_offers_family_provider",
        "meal_commercial_offers",
        ["family_id", "provider_key"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_meal_commercial_offers_family_provider",
        table_name="meal_commercial_offers",
    )
    op.drop_index(
        "ix_meal_commercial_offers_availability",
        table_name="meal_commercial_offers",
    )
    op.drop_table("meal_commercial_offers")
    op.drop_index(
        "ix_meal_source_opening_windows_availability_weekday",
        table_name="meal_source_opening_windows",
    )
    op.drop_table("meal_source_opening_windows")
