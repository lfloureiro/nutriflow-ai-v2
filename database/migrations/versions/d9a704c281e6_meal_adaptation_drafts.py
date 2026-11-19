"""Store incomplete adaptation choices without applying them to meals.

Revision ID: d9a704c281e6
Revises: c2a91f4e780d
"""
import sqlalchemy as sa
from alembic import op

revision = "d9a704c281e6"
down_revision = "c2a91f4e780d"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("meal_adaptation_drafts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("family_id", sa.Uuid(), sa.ForeignKey("families.id", ondelete="CASCADE"), nullable=False),
        sa.Column("base_recipe_id", sa.Uuid(), sa.ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("meal_event_id", sa.Uuid(), sa.ForeignKey("meal_events.id", ondelete="SET NULL"), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("base_fingerprint", sa.String(64), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"))
    op.create_index("ix_meal_adaptation_drafts_family_id", "meal_adaptation_drafts", ["family_id"])
    op.create_index("ix_meal_adaptation_drafts_base_recipe_id", "meal_adaptation_drafts", ["base_recipe_id"])


def downgrade():
    op.drop_table("meal_adaptation_drafts")
