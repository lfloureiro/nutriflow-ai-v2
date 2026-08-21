"""add nutrition targets

Revision ID: c7f4e2a9b1d3
Revises: a6d3c8f1e2b4
Create Date: 2026-08-21 16:25:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c7f4e2a9b1d3"
down_revision: Union[str, Sequence[str], None] = "a6d3c8f1e2b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "nutrition_targets",
        sa.Column("person_id", sa.Uuid(), nullable=False),
        sa.Column("nutrition_goal_id", sa.Uuid(), nullable=True),
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("valid_until", sa.Date(), nullable=True),
        sa.Column("estimated_bmr_kcal", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("bmr_method", sa.String(length=80), nullable=True),
        sa.Column("estimated_tdee_kcal", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("tdee_method", sa.String(length=80), nullable=True),
        sa.Column("energy_min_kcal", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("energy_max_kcal", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("calculation_version", sa.String(length=64), nullable=False),
        sa.Column("calculation_inputs", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
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
            "estimated_bmr_kcal IS NULL OR estimated_bmr_kcal > 0",
            name="ck_nutrition_targets_bmr_positive",
        ),
        sa.CheckConstraint(
            "estimated_tdee_kcal IS NULL OR estimated_tdee_kcal > 0",
            name="ck_nutrition_targets_tdee_positive",
        ),
        sa.CheckConstraint(
            "energy_min_kcal IS NULL OR energy_min_kcal > 0",
            name="ck_nutrition_targets_energy_min_positive",
        ),
        sa.CheckConstraint(
            "energy_max_kcal IS NULL OR energy_max_kcal > 0",
            name="ck_nutrition_targets_energy_max_positive",
        ),
        sa.CheckConstraint(
            "energy_min_kcal IS NULL OR energy_max_kcal IS NULL "
            "OR energy_max_kcal >= energy_min_kcal",
            name="ck_nutrition_targets_energy_range_valid",
        ),
        sa.CheckConstraint(
            "valid_until IS NULL OR valid_until >= valid_from",
            name="ck_nutrition_targets_validity_range_valid",
        ),
        sa.ForeignKeyConstraint(["person_id"], ["persons.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["nutrition_goal_id"],
            ["nutrition_goals.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_nutrition_targets_person_valid_from",
        "nutrition_targets",
        ["person_id", "valid_from"],
        unique=False,
    )
    op.create_index(
        "ix_nutrition_targets_person_status",
        "nutrition_targets",
        ["person_id", "status"],
        unique=False,
    )

    op.create_table(
        "nutrition_target_components",
        sa.Column("nutrition_target_id", sa.Uuid(), nullable=False),
        sa.Column("target_type", sa.String(length=32), nullable=False),
        sa.Column("target_key", sa.String(length=120), nullable=False),
        sa.Column("value_min", sa.Numeric(precision=14, scale=4), nullable=True),
        sa.Column("value_max", sa.Numeric(precision=14, scale=4), nullable=True),
        sa.Column("value_target", sa.Numeric(precision=14, scale=4), nullable=True),
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
            "value_min IS NULL OR value_min >= 0",
            name="ck_nutrition_target_components_value_min_nonnegative",
        ),
        sa.CheckConstraint(
            "value_max IS NULL OR value_max >= 0",
            name="ck_nutrition_target_components_value_max_nonnegative",
        ),
        sa.CheckConstraint(
            "value_target IS NULL OR value_target >= 0",
            name="ck_nutrition_target_components_value_target_nonnegative",
        ),
        sa.CheckConstraint(
            "value_min IS NULL OR value_max IS NULL OR value_max >= value_min",
            name="ck_nutrition_target_components_value_range_valid",
        ),
        sa.CheckConstraint(
            "value_min IS NOT NULL OR value_max IS NOT NULL OR value_target IS NOT NULL",
            name="ck_nutrition_target_components_has_value",
        ),
        sa.ForeignKeyConstraint(
            ["nutrition_target_id"],
            ["nutrition_targets.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "nutrition_target_id",
            "target_type",
            "target_key",
            name="uq_nutrition_target_components_target_key",
        ),
    )
    op.create_index(
        "ix_nutrition_target_components_target",
        "nutrition_target_components",
        ["target_type", "target_key"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_nutrition_target_components_target",
        table_name="nutrition_target_components",
    )
    op.drop_table("nutrition_target_components")
    op.drop_index("ix_nutrition_targets_person_status", table_name="nutrition_targets")
    op.drop_index("ix_nutrition_targets_person_valid_from", table_name="nutrition_targets")
    op.drop_table("nutrition_targets")
