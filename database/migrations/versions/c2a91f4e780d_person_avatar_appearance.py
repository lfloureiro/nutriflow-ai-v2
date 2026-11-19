"""Persist visual avatar preferences independently of demographic inputs.

Revision ID: c2a91f4e780d
Revises: b781e265c904
"""

import sqlalchemy as sa
from alembic import op

revision = "c2a91f4e780d"
down_revision = "b781e265c904"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("persons", sa.Column("avatar_appearance", sa.JSON(), nullable=True))


def downgrade():
    op.drop_column("persons", "avatar_appearance")
