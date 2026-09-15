"""add nutrition plan guidance

Revision ID: b9e3f7c1d4a6
Revises: a8f2c6d4e1b9
Create Date: 2026-09-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b9e3f7c1d4a6"
down_revision: str | Sequence[str] | None = "a8f2c6d4e1b9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "nutrition_plans",
        sa.Column("person_id", sa.Uuid(), nullable=False),
        sa.Column("lineage_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("supersedes_plan_id", sa.Uuid(), nullable=True),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("source_name", sa.String(length=160), nullable=True),
        sa.Column("source_reference", sa.String(length=500), nullable=True),
        sa.Column("original_text", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("valid_until", sa.Date(), nullable=True),
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
        sa.CheckConstraint("version > 0", name="ck_nutrition_plans_version_positive"),
        sa.CheckConstraint(
            "status IN ('draft', 'active', 'inactive', 'superseded')",
            name="ck_nutrition_plans_status_valid",
        ),
        sa.CheckConstraint(
            "source_type IN ('nutritionist', 'clinician', 'user', 'system', 'imported')",
            name="ck_nutrition_plans_source_type_valid",
        ),
        sa.CheckConstraint(
            "valid_until IS NULL OR valid_until >= valid_from",
            name="ck_nutrition_plans_validity_range_valid",
        ),
        sa.ForeignKeyConstraint(["person_id"], ["persons.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["supersedes_plan_id"],
            ["nutrition_plans.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "person_id",
            "lineage_id",
            "version",
            name="uq_nutrition_plans_person_lineage_version",
        ),
    )
    op.create_index(
        "ix_nutrition_plans_person_status",
        "nutrition_plans",
        ["person_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_nutrition_plans_lineage_version",
        "nutrition_plans",
        ["lineage_id", "version"],
        unique=False,
    )

    op.create_table(
        "nutrition_plan_rules",
        sa.Column("nutrition_plan_id", sa.Uuid(), nullable=False),
        sa.Column("rule_kind", sa.String(length=32), nullable=False),
        sa.Column("nutrition_constraint_id", sa.Uuid(), nullable=True),
        sa.Column("nutrition_target_component_id", sa.Uuid(), nullable=True),
        sa.Column("nutrition_goal_id", sa.Uuid(), nullable=True),
        sa.Column("meal_type", sa.String(length=24), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("valid_from", sa.Date(), nullable=True),
        sa.Column("valid_until", sa.Date(), nullable=True),
        sa.Column("source_statement", sa.Text(), nullable=True),
        sa.Column("applies_outside_plan", sa.Boolean(), nullable=False),
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
            "rule_kind IN ('constraint', 'target_component', 'goal')",
            name="ck_nutrition_plan_rules_kind_valid",
        ),
        sa.CheckConstraint(
            "(rule_kind = 'constraint' AND nutrition_constraint_id IS NOT NULL "
            "AND nutrition_target_component_id IS NULL AND nutrition_goal_id IS NULL) OR "
            "(rule_kind = 'target_component' AND nutrition_constraint_id IS NULL "
            "AND nutrition_target_component_id IS NOT NULL AND nutrition_goal_id IS NULL) OR "
            "(rule_kind = 'goal' AND nutrition_constraint_id IS NULL "
            "AND nutrition_target_component_id IS NULL AND nutrition_goal_id IS NOT NULL)",
            name="ck_nutrition_plan_rules_reference_matches_kind",
        ),
        sa.CheckConstraint(
            "meal_type IS NULL OR meal_type IN ('breakfast', 'lunch', 'snack', 'dinner')",
            name="ck_nutrition_plan_rules_meal_type_valid",
        ),
        sa.CheckConstraint(
            "priority >= 0",
            name="ck_nutrition_plan_rules_priority_nonnegative",
        ),
        sa.CheckConstraint(
            "valid_from IS NULL OR valid_until IS NULL OR valid_until >= valid_from",
            name="ck_nutrition_plan_rules_validity_range_valid",
        ),
        sa.ForeignKeyConstraint(
            ["nutrition_plan_id"],
            ["nutrition_plans.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["nutrition_constraint_id"],
            ["nutrition_constraints.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["nutrition_target_component_id"],
            ["nutrition_target_components.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["nutrition_goal_id"],
            ["nutrition_goals.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_nutrition_plan_rules_plan_kind",
        "nutrition_plan_rules",
        ["nutrition_plan_id", "rule_kind"],
        unique=False,
    )
    op.create_index(
        "ix_nutrition_plan_rules_constraint",
        "nutrition_plan_rules",
        ["nutrition_constraint_id"],
        unique=False,
    )
    op.create_index(
        "ix_nutrition_plan_rules_target_component",
        "nutrition_plan_rules",
        ["nutrition_target_component_id"],
        unique=False,
    )
    op.create_index(
        "ix_nutrition_plan_rules_goal",
        "nutrition_plan_rules",
        ["nutrition_goal_id"],
        unique=False,
    )

    op.create_table(
        "nutrition_plan_guidelines",
        sa.Column("nutrition_plan_id", sa.Uuid(), nullable=False),
        sa.Column("guideline_type", sa.String(length=24), nullable=False),
        sa.Column("target_type", sa.String(length=32), nullable=True),
        sa.Column("target_key", sa.String(length=120), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("meal_type", sa.String(length=24), nullable=True),
        sa.Column("period", sa.String(length=24), nullable=True),
        sa.Column("minimum_occurrences", sa.Integer(), nullable=True),
        sa.Column("maximum_occurrences", sa.Integer(), nullable=True),
        sa.Column("severity", sa.String(length=24), nullable=False),
        sa.Column("is_mandatory", sa.Boolean(), nullable=False),
        sa.Column("confirmation_status", sa.String(length=24), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("valid_from", sa.Date(), nullable=True),
        sa.Column("valid_until", sa.Date(), nullable=True),
        sa.Column("source_statement", sa.Text(), nullable=True),
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
            "guideline_type IN ('qualitative', 'frequency')",
            name="ck_nutrition_plan_guidelines_type_valid",
        ),
        sa.CheckConstraint(
            "meal_type IS NULL OR meal_type IN ('breakfast', 'lunch', 'snack', 'dinner')",
            name="ck_nutrition_plan_guidelines_meal_type_valid",
        ),
        sa.CheckConstraint(
            "confirmation_status IN ('proposed', 'confirmed', 'rejected')",
            name="ck_nutrition_plan_guidelines_confirmation_status_valid",
        ),
        sa.CheckConstraint(
            "priority >= 0",
            name="ck_nutrition_plan_guidelines_priority_nonnegative",
        ),
        sa.CheckConstraint(
            "minimum_occurrences IS NULL OR minimum_occurrences >= 0",
            name="ck_nutrition_plan_guidelines_min_occurrences_nonnegative",
        ),
        sa.CheckConstraint(
            "maximum_occurrences IS NULL OR maximum_occurrences >= 0",
            name="ck_nutrition_plan_guidelines_max_occurrences_nonnegative",
        ),
        sa.CheckConstraint(
            "minimum_occurrences IS NULL OR maximum_occurrences IS NULL "
            "OR maximum_occurrences >= minimum_occurrences",
            name="ck_nutrition_plan_guidelines_occurrence_range_valid",
        ),
        sa.CheckConstraint(
            "guideline_type != 'frequency' OR "
            "(period = 'week' AND "
            "(minimum_occurrences IS NOT NULL OR maximum_occurrences IS NOT NULL))",
            name="ck_nutrition_plan_guidelines_frequency_shape_valid",
        ),
        sa.CheckConstraint(
            "guideline_type != 'qualitative' OR "
            "(period IS NULL AND minimum_occurrences IS NULL "
            "AND maximum_occurrences IS NULL)",
            name="ck_nutrition_plan_guidelines_qualitative_shape_valid",
        ),
        sa.CheckConstraint(
            "valid_from IS NULL OR valid_until IS NULL OR valid_until >= valid_from",
            name="ck_nutrition_plan_guidelines_validity_range_valid",
        ),
        sa.ForeignKeyConstraint(
            ["nutrition_plan_id"],
            ["nutrition_plans.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_nutrition_plan_guidelines_plan_type",
        "nutrition_plan_guidelines",
        ["nutrition_plan_id", "guideline_type"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_nutrition_plan_guidelines_plan_type",
        table_name="nutrition_plan_guidelines",
    )
    op.drop_table("nutrition_plan_guidelines")

    op.drop_index("ix_nutrition_plan_rules_goal", table_name="nutrition_plan_rules")
    op.drop_index(
        "ix_nutrition_plan_rules_target_component",
        table_name="nutrition_plan_rules",
    )
    op.drop_index("ix_nutrition_plan_rules_constraint", table_name="nutrition_plan_rules")
    op.drop_index("ix_nutrition_plan_rules_plan_kind", table_name="nutrition_plan_rules")
    op.drop_table("nutrition_plan_rules")

    op.drop_index("ix_nutrition_plans_lineage_version", table_name="nutrition_plans")
    op.drop_index("ix_nutrition_plans_person_status", table_name="nutrition_plans")
    op.drop_table("nutrition_plans")
