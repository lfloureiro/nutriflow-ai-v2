import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator

from app.schemas.meal_recommendation import MealRecommendationCandidateInput
from app.schemas.meal_transformation import MealTransformationOperationRead
from app.schemas.meal_type import MealType
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


class SharedWeeklyPlanParticipantRead(BaseModel):
    person_id: uuid.UUID
    score: Decimal | None
    quantity: Decimal
    quantity_unit: str
    energy_kcal: Decimal | None
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


class SharedWeeklyPlanSlotAcceptanceCreate(BaseModel):
    proposal: SharedWeeklyPlanProposalCreate
    slot_key: str = Field(min_length=1, max_length=120)
    expected_candidate_key: str = Field(min_length=1, max_length=255)
    expected_recipe_ingredient_id: uuid.UUID | None = None
    expected_replacement_food_item_id: uuid.UUID | None = None

    @model_validator(mode="after")
    def validate_expected_transformation_shape(
        self,
    ) -> "SharedWeeklyPlanSlotAcceptanceCreate":
        if (
            self.expected_recipe_ingredient_id is None
        ) != (
            self.expected_replacement_food_item_id is None
        ):
            raise ValueError(
                "expected transformation ingredient and replacement ids must be provided together."
            )
        return self


class SharedWeeklyPlanSlotAcceptanceRead(BaseModel):
    meal_event_id: uuid.UUID
    status: str
    candidate_key: str
    transformation_application_id: uuid.UUID | None = None


class SharedWeeklyPlanProposalRead(BaseModel):
    family_id: uuid.UUID
    participant_ids: list[uuid.UUID]
    week_start: date
    week_end: date
    engine_version: str
    slot_engine_versions: dict[str, str]
    selected_plan: SharedWeeklyPlanSelectionRead | None
    evaluated_combinations: int
    feasible_combinations: int
    rejected_by_person_weekly_maximum: int
    rejected_by_person_daily_limit: int
    search_strategy: str
    search_space_size: int
    search_truncated: bool
