import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel

from app.schemas.meal_type import MealType
from app.schemas.nutrition_plan import EffectiveNutritionPlanSourceRead

WeeklyFrequencyProgressState = Literal["achieved", "exceeded", "in_progress", "unknown"]
WeeklyFrequencyEvidenceStatus = Literal["evaluated", "unsupported_target"]
WeeklyFrequencyOccurrenceStatus = Literal["completed", "planned"]


class WeeklyFrequencyOccurrenceRead(BaseModel):
    meal_event_id: uuid.UUID
    scheduled_at: datetime
    meal_type: MealType
    status: WeeklyFrequencyOccurrenceStatus
    matched_by: list[str]


class WeeklyFrequencyGuidelineProgressRead(BaseModel):
    guideline_id: uuid.UUID
    description: str
    target_type: str | None
    target_key: str | None
    meal_type: MealType | None
    minimum_occurrences: int | None
    maximum_occurrences: int | None
    severity: str
    is_mandatory: bool
    priority: int
    completed_occurrences: int | None
    planned_occurrences: int | None
    total_occurrences: int | None
    remaining_minimum: int | None
    remaining_capacity: int | None
    unclassified_meal_count: int | None
    counts_are_lower_bound: bool
    state: WeeklyFrequencyProgressState
    evidence_status: WeeklyFrequencyEvidenceStatus
    occurrences: list[WeeklyFrequencyOccurrenceRead]
    source: EffectiveNutritionPlanSourceRead


class WeeklyFrequencyProgressRead(BaseModel):
    person_id: uuid.UUID
    timezone: str
    anchor_date: date
    week_start: date
    week_end: date
    guidelines: list[WeeklyFrequencyGuidelineProgressRead]
