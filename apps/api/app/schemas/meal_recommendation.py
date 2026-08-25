import uuid
from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.meal_type import MealType


class MealRecommendationCandidateInput(BaseModel):
    candidate_kind: Literal["food_item", "recipe"]
    composition_id: uuid.UUID
    quantity: Decimal = Field(gt=0)
    quantity_unit: str = Field(min_length=1, max_length=24)


class MealRecommendationCreate(BaseModel):
    daily_nutrition_state_id: uuid.UUID
    planning_date: date
    meal_type: MealType | None = None
    candidates: list[MealRecommendationCandidateInput] = Field(min_length=1, max_length=100)


class RecommendationNutrientRead(BaseModel):
    value: Decimal
    unit: str


class RecommendationNutritionRead(BaseModel):
    energy_kcal: Decimal | None
    nutrients: dict[str, RecommendationNutrientRead]


class HumanPortionComponentRead(BaseModel):
    name: str
    quantity: Decimal | None
    unit: str
    qualitative: bool


class HumanPortionGuidanceRead(BaseModel):
    kind: Literal["recipe_components", "single_item"]
    components: list[HumanPortionComponentRead]


class MealRecommendationOptionRead(BaseModel):
    id: uuid.UUID
    candidate_key: str
    candidate_name: str
    candidate_kind: str
    quantity: Decimal
    quantity_unit: str
    portion_guidance: HumanPortionGuidanceRead | None = None
    eligible: bool
    rank: int | None
    score: Decimal | None
    score_breakdown: dict[str, Decimal]
    exclusion_reasons: list[str]
    explanation: list[str]
    nutrition: RecommendationNutritionRead


class MealRecommendationRunRead(BaseModel):
    id: uuid.UUID
    person_id: uuid.UUID
    daily_nutrition_state_id: uuid.UUID
    planning_date: date
    meal_type: str | None
    engine_version: str
    options: list[MealRecommendationOptionRead]
