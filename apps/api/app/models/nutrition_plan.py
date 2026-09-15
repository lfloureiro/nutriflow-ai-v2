import uuid
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.nutrition_constraint import NutritionConstraint
    from app.models.nutrition_goal import NutritionGoal
    from app.models.nutrition_target import NutritionTargetComponent
    from app.models.person import Person


class NutritionPlan(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "nutrition_plans"
    __table_args__ = (
        CheckConstraint("version > 0", name="ck_nutrition_plans_version_positive"),
        CheckConstraint(
            "status IN ('draft', 'active', 'inactive', 'superseded')",
            name="ck_nutrition_plans_status_valid",
        ),
        CheckConstraint(
            "source_type IN ('nutritionist', 'clinician', 'user', 'system', 'imported')",
            name="ck_nutrition_plans_source_type_valid",
        ),
        CheckConstraint(
            "valid_until IS NULL OR valid_until >= valid_from",
            name="ck_nutrition_plans_validity_range_valid",
        ),
        UniqueConstraint(
            "person_id",
            "lineage_id",
            "version",
            name="uq_nutrition_plans_person_lineage_version",
        ),
        Index("ix_nutrition_plans_person_status", "person_id", "status"),
        Index("ix_nutrition_plans_lineage_version", "lineage_id", "version"),
    )

    person_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("persons.id", ondelete="CASCADE"),
        nullable=False,
    )
    lineage_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
        default=uuid.uuid4,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    supersedes_plan_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("nutrition_plans.id", ondelete="SET NULL"),
        nullable=True,
    )

    title: Mapped[str] = mapped_column(String(160), nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    source_reference: Mapped[str | None] = mapped_column(String(500), nullable=True)
    original_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[str] = mapped_column(String(24), nullable=False, default="draft")
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)

    person: Mapped["Person"] = relationship(back_populates="nutrition_plans")
    supersedes: Mapped["NutritionPlan | None"] = relationship(
        remote_side="NutritionPlan.id",
        foreign_keys=[supersedes_plan_id],
    )
    rules: Mapped[list["NutritionPlanRule"]] = relationship(
        back_populates="nutrition_plan",
        cascade="all, delete-orphan",
        order_by=lambda: (NutritionPlanRule.priority.desc(), NutritionPlanRule.created_at),
    )
    guidelines: Mapped[list["NutritionPlanGuideline"]] = relationship(
        back_populates="nutrition_plan",
        cascade="all, delete-orphan",
        order_by=lambda: (
            NutritionPlanGuideline.priority.desc(),
            NutritionPlanGuideline.created_at,
        ),
    )


class NutritionPlanRule(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "nutrition_plan_rules"
    __table_args__ = (
        CheckConstraint(
            "rule_kind IN ('constraint', 'target_component', 'goal')",
            name="ck_nutrition_plan_rules_kind_valid",
        ),
        CheckConstraint(
            "(rule_kind = 'constraint' AND nutrition_constraint_id IS NOT NULL "
            "AND nutrition_target_component_id IS NULL AND nutrition_goal_id IS NULL) OR "
            "(rule_kind = 'target_component' AND nutrition_constraint_id IS NULL "
            "AND nutrition_target_component_id IS NOT NULL AND nutrition_goal_id IS NULL) OR "
            "(rule_kind = 'goal' AND nutrition_constraint_id IS NULL "
            "AND nutrition_target_component_id IS NULL AND nutrition_goal_id IS NOT NULL)",
            name="ck_nutrition_plan_rules_reference_matches_kind",
        ),
        CheckConstraint(
            "meal_type IS NULL OR meal_type IN ('breakfast', 'lunch', 'snack', 'dinner')",
            name="ck_nutrition_plan_rules_meal_type_valid",
        ),
        CheckConstraint("priority >= 0", name="ck_nutrition_plan_rules_priority_nonnegative"),
        CheckConstraint(
            "valid_from IS NULL OR valid_until IS NULL OR valid_until >= valid_from",
            name="ck_nutrition_plan_rules_validity_range_valid",
        ),
        Index("ix_nutrition_plan_rules_plan_kind", "nutrition_plan_id", "rule_kind"),
        Index("ix_nutrition_plan_rules_constraint", "nutrition_constraint_id"),
        Index("ix_nutrition_plan_rules_target_component", "nutrition_target_component_id"),
        Index("ix_nutrition_plan_rules_goal", "nutrition_goal_id"),
    )

    nutrition_plan_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("nutrition_plans.id", ondelete="CASCADE"),
        nullable=False,
    )
    rule_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    nutrition_constraint_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("nutrition_constraints.id", ondelete="CASCADE"),
        nullable=True,
    )
    nutrition_target_component_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("nutrition_target_components.id", ondelete="CASCADE"),
        nullable=True,
    )
    nutrition_goal_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("nutrition_goals.id", ondelete="CASCADE"),
        nullable=True,
    )

    meal_type: Mapped[str | None] = mapped_column(String(24), nullable=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    valid_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    source_statement: Mapped[str | None] = mapped_column(Text, nullable=True)
    applies_outside_plan: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    nutrition_plan: Mapped[NutritionPlan] = relationship(back_populates="rules")
    nutrition_constraint: Mapped["NutritionConstraint | None"] = relationship()
    nutrition_target_component: Mapped["NutritionTargetComponent | None"] = relationship()
    nutrition_goal: Mapped["NutritionGoal | None"] = relationship()

    @property
    def reference_id(self) -> uuid.UUID:
        reference_id = (
            self.nutrition_constraint_id
            or self.nutrition_target_component_id
            or self.nutrition_goal_id
        )
        if reference_id is None:
            raise ValueError("Nutrition plan rule has no reference")
        return reference_id


class NutritionPlanGuideline(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "nutrition_plan_guidelines"
    __table_args__ = (
        CheckConstraint(
            "guideline_type IN ('qualitative', 'frequency')",
            name="ck_nutrition_plan_guidelines_type_valid",
        ),
        CheckConstraint(
            "meal_type IS NULL OR meal_type IN ('breakfast', 'lunch', 'snack', 'dinner')",
            name="ck_nutrition_plan_guidelines_meal_type_valid",
        ),
        CheckConstraint(
            "confirmation_status IN ('proposed', 'confirmed', 'rejected')",
            name="ck_nutrition_plan_guidelines_confirmation_status_valid",
        ),
        CheckConstraint("priority >= 0", name="ck_nutrition_plan_guidelines_priority_nonnegative"),
        CheckConstraint(
            "minimum_occurrences IS NULL OR minimum_occurrences >= 0",
            name="ck_nutrition_plan_guidelines_min_occurrences_nonnegative",
        ),
        CheckConstraint(
            "maximum_occurrences IS NULL OR maximum_occurrences >= 0",
            name="ck_nutrition_plan_guidelines_max_occurrences_nonnegative",
        ),
        CheckConstraint(
            "minimum_occurrences IS NULL OR maximum_occurrences IS NULL "
            "OR maximum_occurrences >= minimum_occurrences",
            name="ck_nutrition_plan_guidelines_occurrence_range_valid",
        ),
        CheckConstraint(
            "guideline_type != 'frequency' OR "
            "(period = 'week' AND "
            "(minimum_occurrences IS NOT NULL OR maximum_occurrences IS NOT NULL))",
            name="ck_nutrition_plan_guidelines_frequency_shape_valid",
        ),
        CheckConstraint(
            "guideline_type != 'qualitative' OR "
            "(period IS NULL AND minimum_occurrences IS NULL AND maximum_occurrences IS NULL)",
            name="ck_nutrition_plan_guidelines_qualitative_shape_valid",
        ),
        CheckConstraint(
            "valid_from IS NULL OR valid_until IS NULL OR valid_until >= valid_from",
            name="ck_nutrition_plan_guidelines_validity_range_valid",
        ),
        Index("ix_nutrition_plan_guidelines_plan_type", "nutrition_plan_id", "guideline_type"),
    )

    nutrition_plan_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("nutrition_plans.id", ondelete="CASCADE"),
        nullable=False,
    )
    guideline_type: Mapped[str] = mapped_column(String(24), nullable=False)
    target_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    target_key: Mapped[str | None] = mapped_column(String(120), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    meal_type: Mapped[str | None] = mapped_column(String(24), nullable=True)
    period: Mapped[str | None] = mapped_column(String(24), nullable=True)
    minimum_occurrences: Mapped[int | None] = mapped_column(Integer, nullable=True)
    maximum_occurrences: Mapped[int | None] = mapped_column(Integer, nullable=True)
    severity: Mapped[str] = mapped_column(String(24), nullable=False, default="advisory")
    is_mandatory: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    confirmation_status: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        default="confirmed",
    )
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    valid_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    source_statement: Mapped[str | None] = mapped_column(Text, nullable=True)

    nutrition_plan: Mapped[NutritionPlan] = relationship(back_populates="guidelines")
