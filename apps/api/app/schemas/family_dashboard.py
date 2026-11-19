import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel

from app.schemas.avatar import AvatarAppearance


class FamilyDashboardHealthRead(BaseModel):
    state_date: date
    latest_weight_kg: Decimal | None
    weight_trend_7d_kg: Decimal | None
    weight_trend_28d_kg: Decimal | None
    steps: int | None
    active_energy_kcal: Decimal | None
    sleep_duration_minutes: int | None
    resting_heart_rate_bpm: Decimal | None
    hrv_ms: Decimal | None
    training_load: Decimal | None
    confidence_score: Decimal | None
    computed_at: datetime


class FamilyDashboardNutritionRead(BaseModel):
    state_date: date
    energy_consumed_kcal: Decimal
    energy_planned_kcal: Decimal
    energy_remaining_min_kcal: Decimal | None
    energy_remaining_max_kcal: Decimal | None
    adherence_score: Decimal | None
    confidence_score: Decimal | None
    computed_at: datetime


class FamilyDashboardMemberRead(BaseModel):
    avatar_appearance: AvatarAppearance | None = None
    person_id: uuid.UUID
    first_name: str
    last_name: str | None
    timezone: str
    age_years: int | None = None
    sex_for_energy_calculation: Literal["male", "female"] | None = None
    health: FamilyDashboardHealthRead | None
    nutrition: FamilyDashboardNutritionRead | None


class FamilyDashboardMealRead(BaseModel):
    id: uuid.UUID
    meal_type: str
    title: str | None
    scheduled_at: datetime
    timezone: str
    status: str
    location: str | None
    participant_person_ids: list[uuid.UUID]


class FamilyDashboardRead(BaseModel):
    family_id: uuid.UUID
    family_name: str
    timezone: str
    dashboard_date: date
    members: list[FamilyDashboardMemberRead]
    meals: list[FamilyDashboardMealRead]
