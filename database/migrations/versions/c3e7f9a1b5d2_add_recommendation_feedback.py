"""add recommendation feedback

Revision ID: c3e7f9a1b5d2
Revises: a2d6e8f1c3b5
Create Date: 2026-08-21 18:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c3e7f9a1b5d2"
down_revision: Union[str, Sequence[str], None] = "a2d6e8f1c3b5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "meal_recommendation_runs",
        sa.Column("person_id", sa.Uuid(), nullable=False),
        sa.Column("daily_nutrition_state_id", sa.Uuid(), nullable=True),
        sa.Column("planning_date", sa.Date(), nullable=False),
        sa.Column("meal_type", sa.String(length=32), nullable=True),
        sa.Column("engine_version", sa.String(length=64), nullable=False),
        sa.Column("context", sa.JSON(), nullable=True),
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
            "length(engine_version) > 0",
            name="ck_meal_recommendation_runs_engine_version_nonempty",
        ),
        sa.ForeignKeyConstraint(
            ["daily_nutrition_state_id"],
            ["daily_nutrition_states.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["person_id"], ["persons.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_meal_recommendation_runs_person_date",
        "meal_recommendation_runs",
        ["person_id", "planning_date"],
        unique=False,
    )

    op.create_table(
        "meal_recommendation_options",
        sa.Column("recommendation_run_id", sa.Uuid(), nullable=False),
        sa.Column("food_item_id", sa.Uuid(), nullable=True),
        sa.Column("recipe_id", sa.Uuid(), nullable=True),
        sa.Column("food_composition_snapshot_id", sa.Uuid(), nullable=True),
        sa.Column("recipe_composition_snapshot_id", sa.Uuid(), nullable=True),
        sa.Column("candidate_key", sa.String(length=160), nullable=False),
        sa.Column("candidate_name", sa.String(length=160), nullable=False),
        sa.Column("candidate_kind", sa.String(length=32), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=14, scale=4), nullable=False),
        sa.Column("quantity_unit", sa.String(length=24), nullable=False),
        sa.Column("eligible", sa.Boolean(), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=True),
        sa.Column("score", sa.Numeric(precision=14, scale=4), nullable=True),
        sa.Column("score_breakdown", sa.JSON(), nullable=True),
        sa.Column("exclusion_reasons", sa.JSON(), nullable=False),
        sa.Column("explanation", sa.JSON(), nullable=False),
        sa.Column("candidate_subjects", sa.JSON(), nullable=False),
        sa.Column("nutrition_snapshot", sa.JSON(), nullable=False),
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
            "quantity > 0",
            name="ck_meal_recommendation_options_quantity_positive",
        ),
        sa.CheckConstraint(
            "food_item_id IS NULL OR recipe_id IS NULL",
            name="ck_meal_recommendation_options_single_catalog_reference",
        ),
        sa.CheckConstraint(
            "food_composition_snapshot_id IS NULL OR recipe_composition_snapshot_id IS NULL",
            name="ck_meal_recommendation_options_single_composition_reference",
        ),
        sa.CheckConstraint(
            "(eligible AND rank IS NOT NULL AND rank > 0 AND score IS NOT NULL) "
            "OR (NOT eligible AND rank IS NULL AND score IS NULL)",
            name="ck_meal_recommendation_options_evaluation_shape_valid",
        ),
        sa.ForeignKeyConstraint(
            ["food_composition_snapshot_id"],
            ["food_composition_snapshots.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["food_item_id"], ["food_items.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["recipe_composition_snapshot_id"],
            ["recipe_composition_snapshots.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["recipe_id"], ["recipes.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["recommendation_run_id"],
            ["meal_recommendation_runs.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "recommendation_run_id",
            "candidate_kind",
            "candidate_key",
            name="uq_meal_recommendation_options_run_candidate",
        ),
    )
    op.create_index(
        "ix_meal_recommendation_options_run_rank",
        "meal_recommendation_options",
        ["recommendation_run_id", "rank"],
        unique=False,
    )
    op.create_index(
        "ix_meal_recommendation_options_candidate",
        "meal_recommendation_options",
        ["candidate_kind", "candidate_key"],
        unique=False,
    )

    op.create_table(
        "meal_recommendation_feedback",
        sa.Column("recommendation_option_id", sa.Uuid(), nullable=False),
        sa.Column("resulting_serving_id", sa.Uuid(), nullable=True),
        sa.Column("action", sa.String(length=16), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("feedback_metadata", sa.JSON(), nullable=True),
        sa.Column(
            "recorded_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
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
            "action IN ('accepted', 'rejected', 'modified')",
            name="ck_meal_recommendation_feedback_action_valid",
        ),
        sa.CheckConstraint(
            "length(source) > 0",
            name="ck_meal_recommendation_feedback_source_nonempty",
        ),
        sa.ForeignKeyConstraint(
            ["recommendation_option_id"],
            ["meal_recommendation_options.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["resulting_serving_id"],
            ["servings.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_meal_recommendation_feedback_option_recorded_at",
        "meal_recommendation_feedback",
        ["recommendation_option_id", "recorded_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_meal_recommendation_feedback_option_recorded_at",
        table_name="meal_recommendation_feedback",
    )
    op.drop_table("meal_recommendation_feedback")

    op.drop_index(
        "ix_meal_recommendation_options_candidate",
        table_name="meal_recommendation_options",
    )
    op.drop_index(
        "ix_meal_recommendation_options_run_rank",
        table_name="meal_recommendation_options",
    )
    op.drop_table("meal_recommendation_options")

    op.drop_index(
        "ix_meal_recommendation_runs_person_date",
        table_name="meal_recommendation_runs",
    )
    op.drop_table("meal_recommendation_runs")
