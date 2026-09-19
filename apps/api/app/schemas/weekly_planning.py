import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.schemas.meal_plan_fit import (
    MealPlanFitGuidelineRead,
    MealPlanFitRuleRead,
    MealPlanFitStatus,
)
from app.schemas.meal_recommendation import (
    MealRecommendationCandidateInput,
    RecommendationNutritionRead,
)
from app.schemas.meal_transformation import MealTransformationOperationRead
from app.schemas.meal_type import MealType
from app.schemas.nutrition_plan import (
    EffectiveNutritionPlanConflictRead,
    NutritionPlanAuthorityState,
)
from app.schemas.practical_recommendation import (
    PracticalSourceKind,
    RecommendationHistoryHint,
)


class SharedWeeklyPlanningSlotCreate(BaseModel):
    slot_key: str = Field(min_length=1, max_length=120)
    planning_date: date
    scheduled_at: datetime
    meal_type: MealType
    candidates: list[MealRecommendationCandidateInput] = Field(min_length=1, max_length=100)
    location: str | None = Field(default=None, max_length=255)
    available_minutes: int | None = Field(default=None, ge=0)
    has_kitchen: bool | None = None
    source_kinds: list[PracticalSourceKind] = Field(
        default_factory=lambda: ["home", "pantry", "restaurant", "delivery"],
        min_length=1,
        max_length=5,
    )
    delivery_provider_keys: list[str] = Field(default_factory=list, max_length=20)
    provisional_history: list[RecommendationHistoryHint] = Field(
        default_factory=list,
        max_length=14,
    )
    auto_size_portions: bool = False


class SharedWeeklyPlanProposalCreate(BaseModel):
    person_ids: list[uuid.UUID] = Field(min_length=2, max_length=20)
    slots: list[SharedWeeklyPlanningSlotCreate] = Field(min_length=1, max_length=28)
    max_combinations: int = Field(default=10_000, ge=1, le=10_000)


class SharedWeeklyPlanFitDetailRead(BaseModel):
    eligible: bool
    status: MealPlanFitStatus
    fit_score: Decimal | None
    conflicts: list[EffectiveNutritionPlanConflictRead] = Field(default_factory=list)
    safety_issues: list[str] = Field(default_factory=list)
    rule_results: list[MealPlanFitRuleRead] = Field(default_factory=list)
    guideline_results: list[MealPlanFitGuidelineRead] = Field(default_factory=list)


class SharedWeeklyPlanParticipantRead(BaseModel):
    person_id: uuid.UUID
    daily_nutrition_state_id: uuid.UUID | None
    score: Decimal | None
    quantity: Decimal
    quantity_unit: str
    energy_kcal: Decimal | None
    nutrition: RecommendationNutritionRead
    plan_fit_detail: SharedWeeklyPlanFitDetailRead
    portion_factor: Decimal | None
    meal_energy_target_min_kcal: Decimal | None
    meal_energy_target_max_kcal: Decimal | None
    nutrition_plan_authority: NutritionPlanAuthorityState
    active_plan_titles: list[str] = Field(default_factory=list)
    explanation: list[str]


class SharedWeeklyPlanTransformationRead(BaseModel):
    kind: str
    recipe_id: uuid.UUID
    operation: MealTransformationOperationRead
    plan_improvement_participants: int
    preference_improvement_participants: int
    explanation: list[str]


class SharedWeeklyPlanChoiceRead(BaseModel):
    slot_key: str
    planning_date: date
    scheduled_at: datetime
    meal_type: MealType
    candidate_key: str
    candidate_name: str
    candidate_kind: str
    recipe_id: uuid.UUID | None = None
    minimum_score: Decimal | None
    average_score: Decimal | None
    participants: list[SharedWeeklyPlanParticipantRead]
    transformation: SharedWeeklyPlanTransformationRead | None = None


class SharedWeeklyPlanSelectionRead(BaseModel):
    mandatory_support_participants: int
    mandatory_support_total: int
    advisory_support_participants: int
    advisory_support_total: int
    minimum_participant_score: Decimal
    average_participant_score: Decimal
    repeated_candidate_count: int
    choices: list[SharedWeeklyPlanChoiceRead]


class SharedWeeklyPlanSkippedSlotRead(BaseModel):
    slot_key: str
    planning_date: date
    meal_type: MealType
    reason: Literal["no_eligible_candidates"]
    exclusion_reasons: list[str] = Field(default_factory=list)


class SharedWeeklyPlanProposalRead(BaseModel):
    family_id: uuid.UUID
    participant_ids: list[uuid.UUID]
    week_start: date
    week_end: date
    engine_version: str
    slot_engine_versions: dict[str, str]
    selected_plan: SharedWeeklyPlanSelectionRead | None
    skipped_slots: list[SharedWeeklyPlanSkippedSlotRead] = Field(default_factory=list)
    evaluated_combinations: int
    feasible_combinations: int
    rejected_by_person_weekly_maximum: int
    rejected_by_person_daily_limit: int
    search_strategy: str
    search_space_size: int
    search_truncated: bool



class SharedWeeklyPlanExpectedChoiceCreate(BaseModel):
    slot_key: str = Field(min_length=1, max_length=120)
    candidate_key: str = Field(min_length=1, max_length=255)
    recipe_ingredient_id: uuid.UUID | None = None
    replacement_food_item_id: uuid.UUID | None = None

    @model_validator(mode="after")
    def validate_transformation_identity(self) -> "SharedWeeklyPlanExpectedChoiceCreate":
        if (self.recipe_ingredient_id is None) != (self.replacement_food_item_id is None):
            raise ValueError(
                "A weekly transformed choice requires both recipe_ingredient_id "
                "and replacement_food_item_id."
            )
        return self


class SharedWeeklyPlanCreate(SharedWeeklyPlanProposalCreate):
    expected_choices: list[SharedWeeklyPlanExpectedChoiceCreate] = Field(
        min_length=1,
        max_length=28,
    )

    @model_validator(mode="after")
    def validate_expected_choices(self) -> "SharedWeeklyPlanCreate":
        slot_keys = [item.slot_key for item in self.expected_choices]
        if len(slot_keys) != len(set(slot_keys)):
            raise ValueError("Each expected weekly slot may appear only once.")
        return self


class SharedWeeklyPlanMaterializedChoiceRead(BaseModel):
    slot_key: str
    meal_event_id: uuid.UUID
    candidate_key: str
    transformation_application_id: uuid.UUID | None = None
    serving_ids: list[uuid.UUID]


class SharedWeeklyPlanRead(BaseModel):
    family_id: uuid.UUID
    status: Literal["planned"]
    choices: list[SharedWeeklyPlanMaterializedChoiceRead]
