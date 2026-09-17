import uuid
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.schemas.meal_plan_fit import MealPlanFitRead
from app.schemas.meal_transformation import MealTransformationOperationRead
from app.schemas.meal_type import MealType

SharedMealTransformationKind = Literal["plan_adapted", "preference_variant"]


class SharedMealTransformationParticipantCreate(BaseModel):
    person_id: uuid.UUID
    daily_nutrition_state_id: uuid.UUID | None = None
    quantity: Decimal = Field(gt=0)
    quantity_unit: str = Field(min_length=1, max_length=24)


class SharedMealTransformationCreate(BaseModel):
    planning_date: str
    meal_type: MealType
    recipe_id: uuid.UUID
    participants: list[SharedMealTransformationParticipantCreate] = Field(
        min_length=2,
        max_length=20,
    )
    max_proposals: int = Field(default=5, ge=1, le=10)

    @model_validator(mode="after")
    def validate_participants(self) -> "SharedMealTransformationCreate":
        person_ids = [item.person_id for item in self.participants]
        if len(person_ids) != len(set(person_ids)):
            raise ValueError("Each Person may appear only once in a shared transformation request.")
        return self


class SharedMealTransformationParticipantRead(BaseModel):
    person_id: uuid.UUID
    before_fit: MealPlanFitRead
    after_fit: MealPlanFitRead
    plan_score_delta: Decimal | None
    plan_improved_rule_ids: list[str]
    plan_worsened_rule_ids: list[str]
    preference_delta: Decimal


class SharedMealTransformationProposalRead(BaseModel):
    kind: SharedMealTransformationKind
    operation: MealTransformationOperationRead
    participant_results: list[SharedMealTransformationParticipantRead]
    plan_improvement_participants: int
    preference_improvement_participants: int
    minimum_plan_score_delta: Decimal | None
    average_plan_score_delta: Decimal | None
    minimum_preference_delta: Decimal
    average_preference_delta: Decimal
    explanation: list[str]


class SharedMealTransformationBaselineRead(BaseModel):
    person_id: uuid.UUID
    fit: MealPlanFitRead


class SharedMealTransformationRead(BaseModel):
    family_id: uuid.UUID
    recipe_id: uuid.UUID
    recipe_name: str
    planning_date: str
    meal_type: MealType
    baseline: list[SharedMealTransformationBaselineRead]
    proposals: list[SharedMealTransformationProposalRead]
    limitations: list[str]
