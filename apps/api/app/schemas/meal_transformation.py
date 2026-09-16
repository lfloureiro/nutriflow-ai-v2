import uuid
from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.meal_plan_fit import MealPlanFitRead
from app.schemas.meal_type import MealType


class MealTransformationCreate(BaseModel):
    planning_date: date
    meal_type: MealType
    recipe_id: uuid.UUID
    quantity: Decimal = Field(gt=0)
    quantity_unit: str = Field(min_length=1, max_length=24)
    daily_nutrition_state_id: uuid.UUID | None = None
    max_proposals: int = Field(default=5, ge=1, le=10)


class MealTransformationOperationRead(BaseModel):
    operation_type: Literal["replace_ingredient"] = "replace_ingredient"
    substitution_group: str
    recipe_ingredient_id: uuid.UUID
    source_food_item_id: uuid.UUID
    source_food_name: str
    source_quantity: Decimal
    source_unit: str
    replacement_food_item_id: uuid.UUID
    replacement_food_name: str
    replacement_quantity: Decimal
    replacement_unit: str


class MealTransformationProposalRead(BaseModel):
    operation: MealTransformationOperationRead
    before_fit: MealPlanFitRead
    after_fit: MealPlanFitRead
    fit_score_delta: Decimal | None = None
    resolves_mandatory_block: bool
    changed_rule_ids: list[str]
    explanation: list[str]


class MealTransformationRead(BaseModel):
    person_id: uuid.UUID
    recipe_id: uuid.UUID
    recipe_name: str
    planning_date: date
    meal_type: MealType
    baseline_fit: MealPlanFitRead
    proposals: list[MealTransformationProposalRead]
    limitations: list[str]
