import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.meal_type import MealType

NutritionPlanSourceType = Literal["nutritionist", "clinician", "user", "system", "imported"]
NutritionPlanStatus = Literal["draft", "active", "inactive", "superseded"]
NutritionPlanRuleKind = Literal["constraint", "target_component", "goal"]
NutritionPlanGuidelineType = Literal["qualitative", "frequency"]
GuidelineConfirmationStatus = Literal["proposed", "confirmed", "rejected"]


class _ValidityModel(BaseModel):
    @model_validator(mode="after")
    def validate_date_range(self) -> "_ValidityModel":
        start = getattr(self, "valid_from", None)
        end = getattr(self, "valid_until", None)
        if start is not None and end is not None and end < start:
            raise ValueError("valid_until must be on or after valid_from")
        return self


class NutritionPlanCreate(_ValidityModel):
    title: str = Field(min_length=1, max_length=160)
    source_type: NutritionPlanSourceType
    source_name: str | None = Field(default=None, max_length=160)
    source_reference: str | None = Field(default=None, max_length=500)
    original_text: str | None = None
    status: Literal["draft"] = "draft"
    valid_from: date
    valid_until: date | None = None


class NutritionPlanVersionCreate(_ValidityModel):
    title: str | None = Field(default=None, min_length=1, max_length=160)
    source_type: NutritionPlanSourceType | None = None
    source_name: str | None = Field(default=None, max_length=160)
    source_reference: str | None = Field(default=None, max_length=500)
    original_text: str | None = None
    status: Literal["draft", "active", "inactive"] = "draft"
    valid_from: date | None = None
    valid_until: date | None = None


class NutritionPlanUpdate(_ValidityModel):
    title: str | None = Field(default=None, min_length=1, max_length=160)
    source_type: NutritionPlanSourceType | None = None
    source_name: str | None = Field(default=None, max_length=160)
    source_reference: str | None = Field(default=None, max_length=500)
    original_text: str | None = None
    status: NutritionPlanStatus | None = None
    valid_from: date | None = None
    valid_until: date | None = None


class NutritionPlanRuleCreate(_ValidityModel):
    rule_kind: NutritionPlanRuleKind
    reference_id: uuid.UUID
    meal_type: MealType | None = None
    priority: int = Field(default=100, ge=0, le=10000)
    valid_from: date | None = None
    valid_until: date | None = None
    source_statement: str | None = None
    applies_outside_plan: bool = False


class NutritionPlanGuidelineCreate(_ValidityModel):
    guideline_type: NutritionPlanGuidelineType
    target_type: str | None = Field(default=None, max_length=32)
    target_key: str | None = Field(default=None, max_length=120)
    description: str = Field(min_length=1)
    meal_type: MealType | None = None
    period: Literal["week"] | None = None
    minimum_occurrences: int | None = Field(default=None, ge=0)
    maximum_occurrences: int | None = Field(default=None, ge=0)
    severity: str = Field(default="advisory", max_length=24)
    is_mandatory: bool = False
    confirmation_status: GuidelineConfirmationStatus = "confirmed"
    priority: int = Field(default=100, ge=0, le=10000)
    valid_from: date | None = None
    valid_until: date | None = None
    source_statement: str | None = None

    @model_validator(mode="after")
    def validate_guideline_shape(self) -> "NutritionPlanGuidelineCreate":
        if self.guideline_type == "frequency":
            if self.period != "week":
                raise ValueError("frequency guidelines require period='week'")
            if self.minimum_occurrences is None and self.maximum_occurrences is None:
                raise ValueError(
                    "frequency guidelines require a minimum or maximum occurrence count"
                )
        else:
            if self.period is not None:
                raise ValueError("qualitative guidelines cannot define a period")
            if self.minimum_occurrences is not None or self.maximum_occurrences is not None:
                raise ValueError("qualitative guidelines cannot define occurrence counts")
        if (
            self.minimum_occurrences is not None
            and self.maximum_occurrences is not None
            and self.maximum_occurrences < self.minimum_occurrences
        ):
            raise ValueError("maximum_occurrences must be >= minimum_occurrences")
        return self


class NutritionPlanGuidelineUpdate(NutritionPlanGuidelineCreate):
    pass


class NutritionPlanRuleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nutrition_plan_id: uuid.UUID
    rule_kind: NutritionPlanRuleKind
    reference_id: uuid.UUID
    meal_type: MealType | None
    priority: int
    valid_from: date | None
    valid_until: date | None
    source_statement: str | None
    applies_outside_plan: bool
    created_at: datetime
    updated_at: datetime


class NutritionPlanGuidelineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nutrition_plan_id: uuid.UUID
    guideline_type: NutritionPlanGuidelineType
    target_type: str | None
    target_key: str | None
    description: str
    meal_type: MealType | None
    period: str | None
    minimum_occurrences: int | None
    maximum_occurrences: int | None
    severity: str
    is_mandatory: bool
    confirmation_status: GuidelineConfirmationStatus
    priority: int
    valid_from: date | None
    valid_until: date | None
    source_statement: str | None
    created_at: datetime
    updated_at: datetime


class NutritionPlanRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    person_id: uuid.UUID
    lineage_id: uuid.UUID
    version: int
    supersedes_plan_id: uuid.UUID | None
    title: str
    source_type: NutritionPlanSourceType
    source_name: str | None
    source_reference: str | None
    original_text: str | None
    status: NutritionPlanStatus
    valid_from: date
    valid_until: date | None
    created_at: datetime
    updated_at: datetime


class NutritionPlanDetailRead(NutritionPlanRead):
    rules: list[NutritionPlanRuleRead]
    guidelines: list[NutritionPlanGuidelineRead]


class EffectiveNutritionPlanSourceRead(BaseModel):
    plan_id: uuid.UUID | None
    plan_title: str | None
    plan_source_type: str | None
    source_name: str | None
    source_reference: str | None
    rule_source: str | None


class EffectiveNutritionNumericRuleRead(BaseModel):
    id: str
    rule_kind: Literal["constraint", "target_component"]
    target_type: str
    target_key: str
    operator: str
    value_min: Decimal | None
    value_max: Decimal | None
    value_target: Decimal | None
    unit: str | None
    severity: str
    is_mandatory: bool
    priority: int
    meal_type: MealType | None
    requires_candidate_evidence: bool = True
    source: EffectiveNutritionPlanSourceRead


class EffectiveNutritionGoalRead(BaseModel):
    id: str
    goal_type: str
    target_weight_kg: Decimal | None
    target_rate_kg_per_week: Decimal | None
    target_date: date | None
    priority: int
    source: EffectiveNutritionPlanSourceRead


class EffectiveNutritionGuidelineRead(BaseModel):
    id: uuid.UUID
    guideline_type: NutritionPlanGuidelineType
    target_type: str | None
    target_key: str | None
    description: str
    meal_type: MealType | None
    period: str | None
    minimum_occurrences: int | None
    maximum_occurrences: int | None
    severity: str
    is_mandatory: bool
    priority: int
    confirmation_status: GuidelineConfirmationStatus
    requires_candidate_evidence: bool = True
    source: EffectiveNutritionPlanSourceRead


class EffectiveNutritionPlanConflictRead(BaseModel):
    target_type: str
    target_key: str
    unit: str | None
    severity: Literal["mandatory", "advisory"]
    rule_ids: list[str]
    message: str


class EffectiveNutritionPlanRead(BaseModel):
    person_id: uuid.UUID
    effective_date: date
    meal_type: MealType
    active_plans: list[NutritionPlanRead]
    numeric_rules: list[EffectiveNutritionNumericRuleRead]
    goals: list[EffectiveNutritionGoalRead]
    guidelines: list[EffectiveNutritionGuidelineRead]
    conflicts: list[EffectiveNutritionPlanConflictRead]
