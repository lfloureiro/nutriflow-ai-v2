import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel


class PlanningNutritionComponentRead(BaseModel):
    target_type: str
    target_key: str
    consumed_value: Decimal | None
    planned_value: Decimal | None
    remaining_min: Decimal | None
    remaining_max: Decimal | None
    unit: str


class PlanningDailyNutritionStateRead(BaseModel):
    id: uuid.UUID
    state_date: date
    timezone: str
    energy_consumed_kcal: Decimal
    energy_planned_kcal: Decimal
    energy_assumed_kcal: Decimal
    energy_remaining_min_kcal: Decimal | None
    energy_remaining_max_kcal: Decimal | None
    calculation_version: str
    computed_at: datetime
    components: list[PlanningNutritionComponentRead]


class PlanningCandidateRead(BaseModel):
    candidate_kind: Literal["food_item", "recipe"]
    composition_id: uuid.UUID
    catalog_key: str
    name: str
    category: str
    brand: str | None
    description: str | None
    reference_quantity: Decimal
    reference_unit: str
    energy_kcal: Decimal | None
    composition_version: str
    composition_at: datetime


class PlanningBootstrapRead(BaseModel):
    person_id: uuid.UUID
    family_id: uuid.UUID
    scheduled_at: datetime
    planning_date: date
    daily_nutrition_state: PlanningDailyNutritionStateRead | None
    candidates: list[PlanningCandidateRead]
