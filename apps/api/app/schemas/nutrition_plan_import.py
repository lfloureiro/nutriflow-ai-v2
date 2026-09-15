import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.meal_type import MealType
from app.schemas.nutrition_plan import NutritionPlanRead, NutritionPlanSourceType

NutritionPlanImportStatus = Literal["review", "applied", "cancelled"]
NutritionPlanImportProposalType = Literal[
    "numeric_rule",
    "qualitative_guideline",
    "frequency_guideline",
    "unclassified",
]
NutritionPlanImportConfirmationStatus = Literal["proposed", "confirmed", "rejected"]


class _ValidityModel(BaseModel):
    @model_validator(mode="after")
    def validate_date_range(self) -> "_ValidityModel":
        start = getattr(self, "valid_from", None)
        end = getattr(self, "valid_until", None)
        if start is not None and end is not None and end < start:
            raise ValueError("valid_until must be on or after valid_from")
        return self


class NutritionPlanImportCreate(_ValidityModel):
    title: str = Field(min_length=1, max_length=160)
    source_type: NutritionPlanSourceType
    source_name: str | None = Field(default=None, max_length=160)
    source_reference: str | None = Field(default=None, max_length=500)
    source_text: str = Field(min_length=1)
    valid_from: date
    valid_until: date | None = None


class NutritionPlanImportProposalCreate(_ValidityModel):
    source_statement: str = Field(min_length=1)
    proposal_type: NutritionPlanImportProposalType
    target_type: str | None = Field(default=None, max_length=32)
    target_key: str | None = Field(default=None, max_length=120)
    operator: str | None = Field(default=None, max_length=24)
    value_min: Decimal | None = Field(default=None, ge=0)
    value_max: Decimal | None = Field(default=None, ge=0)
    value_target: Decimal | None = Field(default=None, ge=0)
    unit: str | None = Field(default=None, max_length=24)
    description: str | None = None
    meal_type: MealType | None = None
    period: Literal["week"] | None = None
    minimum_occurrences: int | None = Field(default=None, ge=0)
    maximum_occurrences: int | None = Field(default=None, ge=0)
    severity: str = Field(default="advisory", max_length=24)
    is_mandatory: bool = False
    priority: int = Field(default=100, ge=0, le=10000)
    valid_from: date | None = None
    valid_until: date | None = None
    confidence: Decimal = Field(default=Decimal("0.5000"), ge=0, le=1)
    confirmation_status: NutritionPlanImportConfirmationStatus = "proposed"
    parser_note: str | None = None
    review_notes: str | None = None

    @model_validator(mode="after")
    def validate_shape(self) -> "NutritionPlanImportProposalCreate":
        if (
            self.value_min is not None
            and self.value_max is not None
            and self.value_max < self.value_min
        ):
            raise ValueError("value_max must be >= value_min")
        if (
            self.minimum_occurrences is not None
            and self.maximum_occurrences is not None
            and self.maximum_occurrences < self.minimum_occurrences
        ):
            raise ValueError("maximum_occurrences must be >= minimum_occurrences")
        if self.proposal_type == "numeric_rule":
            if not self.target_type or not self.target_key or not self.operator:
                raise ValueError("numeric_rule requires target_type, target_key and operator")
            if (
                self.value_min is None
                and self.value_max is None
                and self.value_target is None
            ):
                raise ValueError("numeric_rule requires at least one numeric value")
            if not self.unit:
                raise ValueError("numeric_rule requires unit")
        elif self.proposal_type == "frequency_guideline":
            if self.period != "week":
                raise ValueError("frequency_guideline requires period='week'")
            if self.minimum_occurrences is None and self.maximum_occurrences is None:
                raise ValueError(
                    "frequency_guideline requires a minimum or maximum occurrence count"
                )
            if not self.description:
                raise ValueError("frequency_guideline requires description")
        elif self.proposal_type == "qualitative_guideline":
            if not self.description:
                raise ValueError("qualitative_guideline requires description")
        return self


class NutritionPlanImportProposalUpdate(_ValidityModel):
    proposal_type: NutritionPlanImportProposalType | None = None
    target_type: str | None = Field(default=None, max_length=32)
    target_key: str | None = Field(default=None, max_length=120)
    operator: str | None = Field(default=None, max_length=24)
    value_min: Decimal | None = Field(default=None, ge=0)
    value_max: Decimal | None = Field(default=None, ge=0)
    value_target: Decimal | None = Field(default=None, ge=0)
    unit: str | None = Field(default=None, max_length=24)
    description: str | None = None
    meal_type: MealType | None = None
    period: Literal["week"] | None = None
    minimum_occurrences: int | None = Field(default=None, ge=0)
    maximum_occurrences: int | None = Field(default=None, ge=0)
    severity: str | None = Field(default=None, max_length=24)
    is_mandatory: bool | None = None
    priority: int | None = Field(default=None, ge=0, le=10000)
    valid_from: date | None = None
    valid_until: date | None = None
    confirmation_status: NutritionPlanImportConfirmationStatus | None = None
    review_notes: str | None = None


class NutritionPlanImportProposalRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    import_session_id: uuid.UUID
    ordinal: int
    source_statement: str
    proposal_type: NutritionPlanImportProposalType
    target_type: str | None
    target_key: str | None
    operator: str | None
    value_min: Decimal | None
    value_max: Decimal | None
    value_target: Decimal | None
    unit: str | None
    description: str | None
    meal_type: MealType | None
    period: str | None
    minimum_occurrences: int | None
    maximum_occurrences: int | None
    severity: str
    is_mandatory: bool
    priority: int
    valid_from: date | None
    valid_until: date | None
    confidence: Decimal
    confirmation_status: NutritionPlanImportConfirmationStatus
    parser_note: str | None
    review_notes: str | None
    nutrition_plan_rule_id: uuid.UUID | None
    nutrition_plan_guideline_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


class NutritionPlanImportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    person_id: uuid.UUID
    nutrition_plan_id: uuid.UUID
    parser_name: str
    parser_version: str
    status: NutritionPlanImportStatus
    source_text: str
    parse_summary: str | None
    created_at: datetime
    updated_at: datetime
    nutrition_plan: NutritionPlanRead
    proposals: list[NutritionPlanImportProposalRead]
