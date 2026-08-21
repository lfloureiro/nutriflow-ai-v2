"""add meal events participants and servings

Revision ID: e1c5b7a9d2f4
Revises: d9f2a7c4e6b1
Create Date: 2026-08-21 17:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e1c5b7a9d2f4"
down_revision: Union[str, Sequence[str], None] = "d9f2a7c4e6b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "meal_events",
        sa.Column("family_id", sa.Uuid(), nullable=False),
        sa.Column("replaces_meal_event_id", sa.Uuid(), nullable=True),
        sa.Column("meal_type", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=True),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("served_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("location", sa.String(length=160), nullable=True),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("source_reference", sa.String(length=255), nullable=True),
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
            "status IN ('planned', 'prepared', 'served', 'completed', 'cancelled', 'replaced')",
            name="ck_meal_events_status_valid",
        ),
        sa.CheckConstraint(
            "completed_at IS NULL OR served_at IS NULL OR completed_at >= served_at",
            name="ck_meal_events_completion_after_serving",
        ),
        sa.CheckConstraint(
            "replaces_meal_event_id IS NULL OR replaces_meal_event_id <> id",
            name="ck_meal_events_not_self_replacing",
        ),
        sa.ForeignKeyConstraint(["family_id"], ["families.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["replaces_meal_event_id"],
            ["meal_events.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_meal_events_family_scheduled_at",
        "meal_events",
        ["family_id", "scheduled_at"],
        unique=False,
    )
    op.create_index(
        "ix_meal_events_family_status",
        "meal_events",
        ["family_id", "status"],
        unique=False,
    )

    op.create_table(
        "meal_participants",
        sa.Column("meal_event_id", sa.Uuid(), nullable=False),
        sa.Column("person_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
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
            "status IN ('planned', 'served', 'consumed', 'partial', 'skipped', 'replaced')",
            name="ck_meal_participants_status_valid",
        ),
        sa.ForeignKeyConstraint(["meal_event_id"], ["meal_events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["person_id"], ["persons.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "meal_event_id",
            "person_id",
            name="uq_meal_participants_event_person",
        ),
    )
    op.create_index(
        "ix_meal_participants_person_event",
        "meal_participants",
        ["person_id", "meal_event_id"],
        unique=False,
    )
    op.create_index(
        "ix_meal_participants_person_status",
        "meal_participants",
        ["person_id", "status"],
        unique=False,
    )

    op.create_table(
        "servings",
        sa.Column("meal_participant_id", sa.Uuid(), nullable=False),
        sa.Column("item_type", sa.String(length=32), nullable=False),
        sa.Column("item_key", sa.String(length=120), nullable=True),
        sa.Column("item_name", sa.String(length=160), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("quantity_planned", sa.Numeric(precision=14, scale=4), nullable=True),
        sa.Column("quantity_served", sa.Numeric(precision=14, scale=4), nullable=True),
        sa.Column("quantity_consumed", sa.Numeric(precision=14, scale=4), nullable=True),
        sa.Column("quantity_unit", sa.String(length=24), nullable=True),
        sa.Column("energy_planned_kcal", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("energy_served_kcal", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("energy_consumed_kcal", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("nutrition_source", sa.String(length=32), nullable=False),
        sa.Column("source_reference", sa.String(length=255), nullable=True),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
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
            "status IN ('planned', 'served', 'consumed', 'partial', 'skipped', 'replaced')",
            name="ck_servings_status_valid",
        ),
        sa.CheckConstraint(
            "quantity_planned IS NULL OR quantity_planned >= 0",
            name="ck_servings_quantity_planned_nonnegative",
        ),
        sa.CheckConstraint(
            "quantity_served IS NULL OR quantity_served >= 0",
            name="ck_servings_quantity_served_nonnegative",
        ),
        sa.CheckConstraint(
            "quantity_consumed IS NULL OR quantity_consumed >= 0",
            name="ck_servings_quantity_consumed_nonnegative",
        ),
        sa.CheckConstraint(
            "energy_planned_kcal IS NULL OR energy_planned_kcal >= 0",
            name="ck_servings_energy_planned_nonnegative",
        ),
        sa.CheckConstraint(
            "energy_served_kcal IS NULL OR energy_served_kcal >= 0",
            name="ck_servings_energy_served_nonnegative",
        ),
        sa.CheckConstraint(
            "energy_consumed_kcal IS NULL OR energy_consumed_kcal >= 0",
            name="ck_servings_energy_consumed_nonnegative",
        ),
        sa.CheckConstraint(
            "quantity_consumed IS NULL OR quantity_served IS NULL "
            "OR quantity_consumed <= quantity_served",
            name="ck_servings_consumed_not_above_served",
        ),
        sa.CheckConstraint(
            "(quantity_planned IS NULL AND quantity_served IS NULL AND quantity_consumed IS NULL) "
            "OR quantity_unit IS NOT NULL",
            name="ck_servings_quantity_unit_present",
        ),
        sa.ForeignKeyConstraint(
            ["meal_participant_id"],
            ["meal_participants.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_servings_participant_status",
        "servings",
        ["meal_participant_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_servings_item",
        "servings",
        ["item_type", "item_key"],
        unique=False,
    )

    op.create_table(
        "serving_nutrition_components",
        sa.Column("serving_id", sa.Uuid(), nullable=False),
        sa.Column("nutrient_key", sa.String(length=120), nullable=False),
        sa.Column("planned_value", sa.Numeric(precision=14, scale=4), nullable=True),
        sa.Column("served_value", sa.Numeric(precision=14, scale=4), nullable=True),
        sa.Column("consumed_value", sa.Numeric(precision=14, scale=4), nullable=True),
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
            "planned_value IS NULL OR planned_value >= 0",
            name="ck_serving_nutrition_components_planned_nonnegative",
        ),
        sa.CheckConstraint(
            "served_value IS NULL OR served_value >= 0",
            name="ck_serving_nutrition_components_served_nonnegative",
        ),
        sa.CheckConstraint(
            "consumed_value IS NULL OR consumed_value >= 0",
            name="ck_serving_nutrition_components_consumed_nonnegative",
        ),
        sa.CheckConstraint(
            "planned_value IS NOT NULL OR served_value IS NOT NULL OR consumed_value IS NOT NULL",
            name="ck_serving_nutrition_components_has_value",
        ),
        sa.ForeignKeyConstraint(["serving_id"], ["servings.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "serving_id",
            "nutrient_key",
            name="uq_serving_nutrition_components_nutrient",
        ),
    )
    op.create_index(
        "ix_serving_nutrition_components_nutrient",
        "serving_nutrition_components",
        ["nutrient_key"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_serving_nutrition_components_nutrient",
        table_name="serving_nutrition_components",
    )
    op.drop_table("serving_nutrition_components")

    op.drop_index("ix_servings_item", table_name="servings")
    op.drop_index("ix_servings_participant_status", table_name="servings")
    op.drop_table("servings")

    op.drop_index("ix_meal_participants_person_status", table_name="meal_participants")
    op.drop_index("ix_meal_participants_person_event", table_name="meal_participants")
    op.drop_table("meal_participants")

    op.drop_index("ix_meal_events_family_status", table_name="meal_events")
    op.drop_index("ix_meal_events_family_scheduled_at", table_name="meal_events")
    op.drop_table("meal_events")
