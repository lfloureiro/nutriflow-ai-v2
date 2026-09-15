import uuid
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.nutrition_plan import NutritionPlan, NutritionPlanGuideline, NutritionPlanRule
    from app.models.person import Person


class NutritionPlanImportSession(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "nutrition_plan_import_sessions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('review', 'applied', 'cancelled')",
            name="ck_nutrition_plan_import_sessions_status_valid",
        ),
        UniqueConstraint(
            "nutrition_plan_id",
            name="uq_nutrition_plan_import_sessions_plan",
        ),
        Index(
            "ix_nutrition_plan_import_sessions_person_status",
            "person_id",
            "status",
        ),
    )

    person_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("persons.id", ondelete="CASCADE"),
        nullable=False,
    )
    nutrition_plan_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("nutrition_plans.id", ondelete="CASCADE"),
        nullable=False,
    )
    parser_name: Mapped[str] = mapped_column(String(64), nullable=False)
    parser_version: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="review")
    source_text: Mapped[str] = mapped_column(Text, nullable=False)
    parse_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    person: Mapped["Person"] = relationship()
    nutrition_plan: Mapped["NutritionPlan"] = relationship()
    proposals: Mapped[list["NutritionPlanImportProposal"]] = relationship(
        back_populates="import_session",
        cascade="all, delete-orphan",
        order_by=lambda: NutritionPlanImportProposal.ordinal,
    )


class NutritionPlanImportProposal(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "nutrition_plan_import_proposals"
    __table_args__ = (
        CheckConstraint(
            "proposal_type IN ('numeric_rule', 'qualitative_guideline', "
            "'frequency_guideline', 'unclassified')",
            name="ck_nutrition_plan_import_proposals_type_valid",
        ),
        CheckConstraint(
            "confirmation_status IN ('proposed', 'confirmed', 'rejected')",
            name="ck_nutrition_plan_import_proposals_confirmation_valid",
        ),
        CheckConstraint(
            "meal_type IS NULL OR meal_type IN ('breakfast', 'lunch', 'snack', 'dinner')",
            name="ck_nutrition_plan_import_proposals_meal_type_valid",
        ),
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_nutrition_plan_import_proposals_confidence_range",
        ),
        CheckConstraint(
            "priority >= 0",
            name="ck_nutrition_plan_import_proposals_priority_nonnegative",
        ),
        CheckConstraint(
            "value_min IS NULL OR value_min >= 0",
            name="ck_nutrition_plan_import_proposals_value_min_nonnegative",
        ),
        CheckConstraint(
            "value_max IS NULL OR value_max >= 0",
            name="ck_nutrition_plan_import_proposals_value_max_nonnegative",
        ),
        CheckConstraint(
            "value_target IS NULL OR value_target >= 0",
            name="ck_nutrition_plan_import_proposals_value_target_nonnegative",
        ),
        CheckConstraint(
            "value_min IS NULL OR value_max IS NULL OR value_max >= value_min",
            name="ck_nutrition_plan_import_proposals_value_range_valid",
        ),
        CheckConstraint(
            "minimum_occurrences IS NULL OR minimum_occurrences >= 0",
            name="ck_nutrition_plan_import_proposals_min_occurrences_nonnegative",
        ),
        CheckConstraint(
            "maximum_occurrences IS NULL OR maximum_occurrences >= 0",
            name="ck_nutrition_plan_import_proposals_max_occurrences_nonnegative",
        ),
        CheckConstraint(
            "minimum_occurrences IS NULL OR maximum_occurrences IS NULL "
            "OR maximum_occurrences >= minimum_occurrences",
            name="ck_nutrition_plan_import_proposals_occurrence_range_valid",
        ),
        CheckConstraint(
            "valid_from IS NULL OR valid_until IS NULL OR valid_until >= valid_from",
            name="ck_nutrition_plan_import_proposals_validity_range_valid",
        ),
        CheckConstraint(
            "NOT (nutrition_plan_rule_id IS NOT NULL "
            "AND nutrition_plan_guideline_id IS NOT NULL)",
            name="ck_nutrition_plan_import_proposals_single_materialization",
        ),
        UniqueConstraint(
            "import_session_id",
            "ordinal",
            name="uq_nutrition_plan_import_proposals_session_ordinal",
        ),
        Index(
            "ix_nutrition_plan_import_proposals_session_confirmation",
            "import_session_id",
            "confirmation_status",
        ),
    )

    import_session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("nutrition_plan_import_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    source_statement: Mapped[str] = mapped_column(Text, nullable=False)
    proposal_type: Mapped[str] = mapped_column(String(32), nullable=False)

    target_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    target_key: Mapped[str | None] = mapped_column(String(120), nullable=True)
    operator: Mapped[str | None] = mapped_column(String(24), nullable=True)
    value_min: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    value_max: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    value_target: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(24), nullable=True)

    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    meal_type: Mapped[str | None] = mapped_column(String(24), nullable=True)
    period: Mapped[str | None] = mapped_column(String(24), nullable=True)
    minimum_occurrences: Mapped[int | None] = mapped_column(Integer, nullable=True)
    maximum_occurrences: Mapped[int | None] = mapped_column(Integer, nullable=True)

    severity: Mapped[str] = mapped_column(String(24), nullable=False, default="advisory")
    is_mandatory: Mapped[bool] = mapped_column(nullable=False, default=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    valid_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)

    confidence: Mapped[Decimal] = mapped_column(
        Numeric(5, 4),
        nullable=False,
        default=Decimal("0.5000"),
    )
    confirmation_status: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        default="proposed",
    )
    parser_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    nutrition_plan_rule_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("nutrition_plan_rules.id", ondelete="SET NULL"),
        nullable=True,
    )
    nutrition_plan_guideline_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("nutrition_plan_guidelines.id", ondelete="SET NULL"),
        nullable=True,
    )

    import_session: Mapped[NutritionPlanImportSession] = relationship(back_populates="proposals")
    nutrition_plan_rule: Mapped["NutritionPlanRule | None"] = relationship()
    nutrition_plan_guideline: Mapped["NutritionPlanGuideline | None"] = relationship()
