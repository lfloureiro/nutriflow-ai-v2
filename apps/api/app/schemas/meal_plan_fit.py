import uuid
from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.meal_recommendation import (
    MealRecommendationCandidateInput,
    RecommendationNutritionRead,
)
from app.schemas.meal_type import MealType
from app.schemas.nutrition_plan import (
    EffectiveNutritionPlanConflictRead,
    EffectiveNutritionPlanSourceRead,
    NutritionPlanRead,
)

MealPlanFitStatus = Literal["pass", "partial", "fail", "unknown", "conflict"]
MealPlanFitRuleStatus = Literal["pass", "fail", "support", "unknown", "not_evaluated"]
MealPlanFitRuleScope = Literal["candidate", "meal", "daily"]
MealPlanFitGuidelineStatus = Literal[
    "pass",
    "fail",
    "support",
    "neutral",
    "unknown",
    "not_evaluated",
]


class MealPlanFitCreate(BaseModel):
    planning_date: date
    meal_type: MealType
    candidate: MealRecommendationCandidateInput
    daily_nutrition_state_id: uuid.UUID | None = None


class MealPlanFitCandidateRead(BaseModel):
    key: str
    name: str
    kind: str
    quantity: Decimal
    quantity_unit: str
    nutrition: RecommendationNutritionRead


class MealPlanFitRuleRead(BaseModel):
    rule_id: str
    target_type: str
    target_key: str
    operator: str
    scope: MealPlanFitRuleScope
    status: MealPlanFitRuleStatus
    is_mandatory: bool
    priority: int
    observed_value: Decimal | None = None
    observed_unit: str | None = None
    current_daily_value: Decimal | None = None
    projected_daily_value: Decimal | None = None
    target_min: Decimal | None = None
    target_max: Decimal | None = None
    target_value: Decimal | None = None
    target_unit: str | None = None
    score: Decimal | None = Field(default=None, ge=0, le=1)
    explanation: str
    source: EffectiveNutritionPlanSourceRead


class MealPlanFitGuidelineRead(BaseModel):
    guideline_id: uuid.UUID
    guideline_type: str = "unknown"
    target_type: str | None = None
    target_key: str | None = None
    description: str
    meal_type: MealType | None = None
    period: str | None = None
    minimum_occurrences: int | None = None
    maximum_occurrences: int | None = None
    current_occurrences: int | None = None
    projected_occurrences: int | None = None
    counts_are_lower_bound: bool = False
    unclassified_meal_count: int | None = Field(default=None, ge=0)
    candidate_matches: bool | None = None
    matched_by: list[str] = Field(default_factory=list)
    is_mandatory: bool
    priority: int
    status: MealPlanFitGuidelineStatus = "not_evaluated"
    explanation: str
    source: EffectiveNutritionPlanSourceRead


class MealPlanFitRead(BaseModel):
    person_id: uuid.UUID
    planning_date: date
    meal_type: MealType
    daily_nutrition_state_id: uuid.UUID | None
    candidate: MealPlanFitCandidateRead
    eligible: bool
    status: MealPlanFitStatus
    fit_score: Decimal | None = Field(default=None, ge=0, le=1)
    active_plans: list[NutritionPlanRead]
    conflicts: list[EffectiveNutritionPlanConflictRead]
    safety_issues: list[str]
    rule_results: list[MealPlanFitRuleRead]
    guideline_results: list[MealPlanFitGuidelineRead]
    explanation: list[str]
