"""add nutrition plan import review

Revision ID: c1f4a8d2e6b9
Revises: b9e3f7c1d4a6
Create Date: 2026-09-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c1f4a8d2e6b9"
down_revision: str | Sequence[str] | None = "b9e3f7c1d4a6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "nutrition_plan_import_sessions",
        sa.Column("person_id", sa.Uuid(), nullable=False),
        sa.Column("nutrition_plan_id", sa.Uuid(), nullable=False),
        sa.Column("parser_name", sa.String(length=64), nullable=False),
        sa.Column("parser_version", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("source_text", sa.Text(), nullable=False),
        sa.Column("parse_summary", sa.Text(), nullable=True),
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
            "status IN ('review', 'applied', 'cancelled')",
            name="ck_nutrition_plan_import_sessions_status_valid",
        ),
        sa.ForeignKeyConstraint(["person_id"], ["persons.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["nutrition_plan_id"],
            ["nutrition_plans.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "nutrition_plan_id",
            name="uq_nutrition_plan_import_sessions_plan",
        ),
    )
    op.create_index(
        "ix_nutrition_plan_import_sessions_person_status",
        "nutrition_plan_import_sessions",
        ["person_id", "status"],
        unique=False,
    )

    op.create_table(
        "nutrition_plan_import_proposals",
        sa.Column("import_session_id", sa.Uuid(), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("source_statement", sa.Text(), nullable=False),
        sa.Column("proposal_type", sa.String(length=32), nullable=False),
        sa.Column("target_type", sa.String(length=32), nullable=True),
        sa.Column("target_key", sa.String(length=120), nullable=True),
        sa.Column("operator", sa.String(length=24), nullable=True),
        sa.Column("value_min", sa.Numeric(14, 4), nullable=True),
        sa.Column("value_max", sa.Numeric(14, 4), nullable=True),
        sa.Column("value_target", sa.Numeric(14, 4), nullable=True),
        sa.Column("unit", sa.String(length=24), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("meal_type", sa.String(length=24), nullable=True),
        sa.Column("period", sa.String(length=24), nullable=True),
        sa.Column("minimum_occurrences", sa.Integer(), nullable=True),
        sa.Column("maximum_occurrences", sa.Integer(), nullable=True),
        sa.Column("severity", sa.String(length=24), nullable=False),
        sa.Column("is_mandatory", sa.Boolean(), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("valid_from", sa.Date(), nullable=True),
        sa.Column("valid_until", sa.Date(), nullable=True),
        sa.Column("confidence", sa.Numeric(5, 4), nullable=False),
        sa.Column("confirmation_status", sa.String(length=24), nullable=False),
        sa.Column("parser_note", sa.Text(), nullable=True),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("nutrition_plan_rule_id", sa.Uuid(), nullable=True),
        sa.Column("nutrition_plan_guideline_id", sa.Uuid(), nullable=True),
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
            "proposal_type IN ('numeric_rule', 'qualitative_guideline', "
            "'frequency_guideline', 'unclassified')",
            name="ck_nutrition_plan_import_proposals_type_valid",
        ),
        sa.CheckConstraint(
            "confirmation_status IN ('proposed', 'confirmed', 'rejected')",
            name="ck_nutrition_plan_import_proposals_confirmation_valid",
        ),
        sa.CheckConstraint(
            "meal_type IS NULL OR meal_type IN ('breakfast', 'lunch', 'snack', 'dinner')",
            name="ck_nutrition_plan_import_proposals_meal_type_valid",
        ),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_nutrition_plan_import_proposals_confidence_range",
        ),
        sa.CheckConstraint(
            "priority >= 0",
            name="ck_nutrition_plan_import_proposals_priority_nonnegative",
        ),
        sa.CheckConstraint(
            "value_min IS NULL OR value_min >= 0",
            name="ck_nutrition_plan_import_proposals_value_min_nonnegative",
        ),
        sa.CheckConstraint(
            "value_max IS NULL OR value_max >= 0",
            name="ck_nutrition_plan_import_proposals_value_max_nonnegative",
        ),
        sa.CheckConstraint(
            "value_target IS NULL OR value_target >= 0",
            name="ck_nutrition_plan_import_proposals_value_target_nonnegative",
        ),
        sa.CheckConstraint(
            "value_min IS NULL OR value_max IS NULL OR value_max >= value_min",
            name="ck_nutrition_plan_import_proposals_value_range_valid",
        ),
        sa.CheckConstraint(
            "minimum_occurrences IS NULL OR minimum_occurrences >= 0",
            name="ck_nutrition_plan_import_proposals_min_occurrences_nonnegative",
        ),
        sa.CheckConstraint(
            "maximum_occurrences IS NULL OR maximum_occurrences >= 0",
            name="ck_nutrition_plan_import_proposals_max_occurrences_nonnegative",
        ),
        sa.CheckConstraint(
            "minimum_occurrences IS NULL OR maximum_occurrences IS NULL "
            "OR maximum_occurrences >= minimum_occurrences",
            name="ck_nutrition_plan_import_proposals_occurrence_range_valid",
        ),
        sa.CheckConstraint(
            "valid_from IS NULL OR valid_until IS NULL OR valid_until >= valid_from",
            name="ck_nutrition_plan_import_proposals_validity_range_valid",
        ),
        sa.CheckConstraint(
            "NOT (nutrition_plan_rule_id IS NOT NULL "
            "AND nutrition_plan_guideline_id IS NOT NULL)",
            name="ck_nutrition_plan_import_proposals_single_materialization",
        ),
        sa.ForeignKeyConstraint(
            ["import_session_id"],
            ["nutrition_plan_import_sessions.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["nutrition_plan_rule_id"],
            ["nutrition_plan_rules.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["nutrition_plan_guideline_id"],
            ["nutrition_plan_guidelines.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "import_session_id",
            "ordinal",
            name="uq_nutrition_plan_import_proposals_session_ordinal",
        ),
    )
    op.create_index(
        "ix_nutrition_plan_import_proposals_session_confirmation",
        "nutrition_plan_import_proposals",
        ["import_session_id", "confirmation_status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_nutrition_plan_import_proposals_session_confirmation",
        table_name="nutrition_plan_import_proposals",
    )
    op.drop_table("nutrition_plan_import_proposals")

    op.drop_index(
        "ix_nutrition_plan_import_sessions_person_status",
        table_name="nutrition_plan_import_sessions",
    )
    op.drop_table("nutrition_plan_import_sessions")
