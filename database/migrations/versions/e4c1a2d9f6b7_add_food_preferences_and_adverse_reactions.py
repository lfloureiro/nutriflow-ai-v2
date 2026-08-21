"""add food preferences and adverse reactions

Revision ID: e4c1a2d9f6b7
Revises: 107e3c7fd825
Create Date: 2026-08-21 15:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e4c1a2d9f6b7"
down_revision: Union[str, Sequence[str], None] = "107e3c7fd825"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "food_preferences",
        sa.Column("person_id", sa.Uuid(), nullable=False),
        sa.Column("subject_type", sa.String(length=32), nullable=False),
        sa.Column("subject_key", sa.String(length=120), nullable=False),
        sa.Column("preference_type", sa.String(length=16), nullable=False),
        sa.Column("intensity", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
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
            "intensity >= 1 AND intensity <= 5",
            name="ck_food_preferences_intensity_range",
        ),
        sa.CheckConstraint(
            "start_date IS NULL OR end_date IS NULL OR end_date >= start_date",
            name="ck_food_preferences_date_range_valid",
        ),
        sa.ForeignKeyConstraint(["person_id"], ["persons.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_food_preferences_person_subject",
        "food_preferences",
        ["person_id", "subject_type", "subject_key"],
        unique=False,
    )

    op.create_table(
        "food_adverse_reactions",
        sa.Column("person_id", sa.Uuid(), nullable=False),
        sa.Column("reaction_type", sa.String(length=24), nullable=False),
        sa.Column("subject_type", sa.String(length=32), nullable=False),
        sa.Column("subject_key", sa.String(length=120), nullable=False),
        sa.Column("severity", sa.String(length=24), nullable=False),
        sa.Column("is_mandatory", sa.Boolean(), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("source_name", sa.String(length=120), nullable=True),
        sa.Column("source_reference", sa.String(length=255), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
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
            "start_date IS NULL OR end_date IS NULL OR end_date >= start_date",
            name="ck_food_adverse_reactions_date_range_valid",
        ),
        sa.ForeignKeyConstraint(["person_id"], ["persons.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_food_adverse_reactions_person_subject",
        "food_adverse_reactions",
        ["person_id", "subject_type", "subject_key", "reaction_type"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ix_food_adverse_reactions_person_subject",
        table_name="food_adverse_reactions",
    )
    op.drop_table("food_adverse_reactions")

    op.drop_index(
        "ix_food_preferences_person_subject",
        table_name="food_preferences",
    )
    op.drop_table("food_preferences")
