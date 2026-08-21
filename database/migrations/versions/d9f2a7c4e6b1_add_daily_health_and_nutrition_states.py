"""add daily health and nutrition states

Revision ID: d9f2a7c4e6b1
Revises: b8e6d4c2a1f9
Create Date: 2026-08-21 17:22:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d9f2a7c4e6b1"
down_revision: Union[str, Sequence[str], None] = "b8e6d4c2a1f9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "daily_health_states",
        sa.Column("person_id", sa.Uuid(), nullable=False),
        sa.Column("state_date", sa.Date(), nullable=False),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.Column("latest_weight_kg", sa.Numeric(precision=8, scale=3), nullable=True),
        sa.Column("weight_trend_7d_kg", sa.Numeric(precision=8, scale=3), nullable=True),
        sa.Column("weight_trend_28d_kg", sa.Numeric(precision=8, scale=3), nullable=True),
        sa.Column("steps", sa.Integer(), nullable=True),
        sa.Column("active_energy_kcal", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("resting_energy_kcal", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column(
            "estimated_expenditure_kcal",
            sa.Numeric(precision=10, scale=2),
            nullable=True,
        ),
        sa.Column("sleep_duration_minutes", sa.Integer(), nullable=True),
        sa.Column(
            "resting_heart_rate_bpm",
            sa.Numeric(precision=8, scale=2),
            nullable=True,
        ),
        sa.Column("hrv_ms", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("training_load", sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column("confidence_score", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column("calculation_version", sa.String(length=64), nullable=False),
        sa.Column("calculation_inputs", sa.JSON(), nullable=True),
        sa.Column("source_window_start_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_window_end_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "computed_at",
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
            "latest_weight_kg IS NULL OR latest_weight_kg > 0",
            name="ck_daily_health_states_weight_positive",
        ),
        sa.CheckConstraint(
            "steps IS NULL OR steps >= 0",
            name="ck_daily_health_states_steps_nonnegative",
        ),
        sa.CheckConstraint(
            "active_energy_kcal IS NULL OR active_energy_kcal >= 0",
            name="ck_daily_health_states_active_energy_nonnegative",
        ),
        sa.CheckConstraint(
            "resting_energy_kcal IS NULL OR resting_energy_kcal >= 0",
            name="ck_daily_health_states_resting_energy_nonnegative",
        ),
        sa.CheckConstraint(
            "estimated_expenditure_kcal IS NULL OR estimated_expenditure_kcal >= 0",
            name="ck_daily_health_states_expenditure_nonnegative",
        ),
        sa.CheckConstraint(
            "sleep_duration_minutes IS NULL OR sleep_duration_minutes >= 0",
            name="ck_daily_health_states_sleep_nonnegative",
        ),
        sa.CheckConstraint(
            "resting_heart_rate_bpm IS NULL OR resting_heart_rate_bpm > 0",
            name="ck_daily_health_states_resting_hr_positive",
        ),
        sa.CheckConstraint(
            "hrv_ms IS NULL OR hrv_ms >= 0",
            name="ck_daily_health_states_hrv_nonnegative",
        ),
        sa.CheckConstraint(
            "training_load IS NULL OR training_load >= 0",
            name="ck_daily_health_states_training_load_nonnegative",
        ),
        sa.CheckConstraint(
            "confidence_score IS NULL OR (confidence_score >= 0 AND confidence_score <= 1)",
            name="ck_daily_health_states_confidence_range",
        ),
        sa.CheckConstraint(
            "source_window_start_at IS NULL OR source_window_end_at IS NULL "
            "OR source_window_end_at >= source_window_start_at",
            name="ck_daily_health_states_source_window_valid",
        ),
        sa.ForeignKeyConstraint(["person_id"], ["persons.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "person_id",
            "state_date",
            "calculation_version",
            name="uq_daily_health_states_person_date_version",
        ),
    )
    op.create_index(
        "ix_daily_health_states_person_date",
        "daily_health_states",
        ["person_id", "state_date"],
        unique=False,
    )

    op.create_table(
        "daily_nutrition_states",
        sa.Column("person_id", sa.Uuid(), nullable=False),
        sa.Column("nutrition_target_id", sa.Uuid(), nullable=True),
        sa.Column("state_date", sa.Date(), nullable=False),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.Column("energy_consumed_kcal", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("energy_planned_kcal", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column(
            "energy_remaining_min_kcal",
            sa.Numeric(precision=10, scale=2),
            nullable=True,
        ),
        sa.Column(
            "energy_remaining_max_kcal",
            sa.Numeric(precision=10, scale=2),
            nullable=True,
        ),
        sa.Column("adherence_score", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column("confidence_score", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column("calculation_version", sa.String(length=64), nullable=False),
        sa.Column("calculation_inputs", sa.JSON(), nullable=True),
        sa.Column(
            "computed_at",
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
            "energy_consumed_kcal >= 0",
            name="ck_daily_nutrition_states_energy_consumed_nonnegative",
        ),
        sa.CheckConstraint(
            "energy_planned_kcal >= 0",
            name="ck_daily_nutrition_states_energy_planned_nonnegative",
        ),
        sa.CheckConstraint(
            "energy_remaining_min_kcal IS NULL OR energy_remaining_max_kcal IS NULL "
            "OR energy_remaining_max_kcal >= energy_remaining_min_kcal",
            name="ck_daily_nutrition_states_energy_remaining_range_valid",
        ),
        sa.CheckConstraint(
            "adherence_score IS NULL OR (adherence_score >= 0 AND adherence_score <= 1)",
            name="ck_daily_nutrition_states_adherence_range",
        ),
        sa.CheckConstraint(
            "confidence_score IS NULL OR (confidence_score >= 0 AND confidence_score <= 1)",
            name="ck_daily_nutrition_states_confidence_range",
        ),
        sa.ForeignKeyConstraint(
            ["nutrition_target_id"],
            ["nutrition_targets.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["person_id"], ["persons.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "person_id",
            "state_date",
            "calculation_version",
            name="uq_daily_nutrition_states_person_date_version",
        ),
    )
    op.create_index(
        "ix_daily_nutrition_states_person_date",
        "daily_nutrition_states",
        ["person_id", "state_date"],
        unique=False,
    )

    op.create_table(
        "daily_nutrition_state_components",
        sa.Column("daily_nutrition_state_id", sa.Uuid(), nullable=False),
        sa.Column("target_type", sa.String(length=32), nullable=False),
        sa.Column("target_key", sa.String(length=120), nullable=False),
        sa.Column("consumed_value", sa.Numeric(precision=14, scale=4), nullable=True),
        sa.Column("planned_value", sa.Numeric(precision=14, scale=4), nullable=True),
        sa.Column("remaining_min", sa.Numeric(precision=14, scale=4), nullable=True),
        sa.Column("remaining_max", sa.Numeric(precision=14, scale=4), nullable=True),
        sa.Column("unit", sa.String(length=24), nullable=False),
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
            "consumed_value IS NULL OR consumed_value >= 0",
            name="ck_daily_nutrition_state_components_consumed_nonnegative",
        ),
        sa.CheckConstraint(
            "planned_value IS NULL OR planned_value >= 0",
            name="ck_daily_nutrition_state_components_planned_nonnegative",
        ),
        sa.CheckConstraint(
            "remaining_min IS NULL OR remaining_max IS NULL OR remaining_max >= remaining_min",
            name="ck_daily_nutrition_state_components_remaining_range_valid",
        ),
        sa.CheckConstraint(
            "consumed_value IS NOT NULL OR planned_value IS NOT NULL "
            "OR remaining_min IS NOT NULL OR remaining_max IS NOT NULL",
            name="ck_daily_nutrition_state_components_has_value",
        ),
        sa.ForeignKeyConstraint(
            ["daily_nutrition_state_id"],
            ["daily_nutrition_states.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "daily_nutrition_state_id",
            "target_type",
            "target_key",
            name="uq_daily_nutrition_state_components_target_key",
        ),
    )
    op.create_index(
        "ix_daily_nutrition_state_components_target",
        "daily_nutrition_state_components",
        ["target_type", "target_key"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_daily_nutrition_state_components_target",
        table_name="daily_nutrition_state_components",
    )
    op.drop_table("daily_nutrition_state_components")
    op.drop_index(
        "ix_daily_nutrition_states_person_date",
        table_name="daily_nutrition_states",
    )
    op.drop_table("daily_nutrition_states")
    op.drop_index(
        "ix_daily_health_states_person_date",
        table_name="daily_health_states",
    )
    op.drop_table("daily_health_states")
