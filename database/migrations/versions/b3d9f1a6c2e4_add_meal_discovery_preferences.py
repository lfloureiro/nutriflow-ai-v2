"""add meal discovery preferences

Revision ID: b3d9f1a6c2e4
Revises: f8c4a1d2e7b9
Create Date: 2026-08-23
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "b3d9f1a6c2e4"
down_revision: str | Sequence[str] | None = "f8c4a1d2e7b9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "families",
        sa.Column(
            "meal_discovery_sources",
            sa.JSON(),
            server_default=sa.text("'[\"shared_recipes\"]'::json"),
            nullable=False,
        ),
    )
    op.add_column(
        "families",
        sa.Column("delivery_address", sa.Text(), nullable=True),
    )
    op.add_column(
        "families",
        sa.Column("restaurant_area", sa.String(length=255), nullable=True),
    )
    op.alter_column("families", "meal_discovery_sources", server_default=None)

    op.add_column(
        "person_profiles",
        sa.Column("meal_discovery_sources_override", sa.JSON(), nullable=True),
    )
    op.add_column(
        "person_profiles",
        sa.Column("delivery_address_override", sa.Text(), nullable=True),
    )
    op.add_column(
        "person_profiles",
        sa.Column("restaurant_area_override", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("person_profiles", "restaurant_area_override")
    op.drop_column("person_profiles", "delivery_address_override")
    op.drop_column("person_profiles", "meal_discovery_sources_override")

    op.drop_column("families", "restaurant_area")
    op.drop_column("families", "delivery_address")
    op.drop_column("families", "meal_discovery_sources")
