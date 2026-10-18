"""Persist immutable shopping receipt provenance.

Revision ID: b781e265c904
Revises: 93c8e18311c4
"""

import sqlalchemy as sa
from alembic import op

revision = "b781e265c904"
down_revision = "93c8e18311c4"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "shopping_list_items", sa.Column("pantry_receipt", sa.JSON(), nullable=True)
    )


def downgrade():
    op.drop_column("shopping_list_items", "pantry_receipt")
