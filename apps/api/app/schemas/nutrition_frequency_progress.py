import uuid
from datetime import date
from typing import Literal

from pydantic import BaseModel

from app.schemas.meal_type import MealType

FrequencyEvidenceStatus = Literal["available", "unknown"]
FrequencyProgressStatus = Literal[
    "within_bounds",
    "below_minimum",
    "above_maximum",
    "unknown",
]


class WeeklyFrequencyGuidelineProgressRead(BaseModel):
    guideline_id: uuid.UUID
    description: str
    target_type: str | None
    target_key: str | None
    meal_type: MealType | None
    minimum_occurrences: int | None
    maximum_occurrences: int | None
    is_mandatory: bool
    severity: str
    evidence_status: FrequencyEvidenceStatus
    current_status: FrequencyProgressStatus
    projected_status: FrequencyProgressStatus
    completed_occurrences: int | None
    planned_occurrences: int | None
    projected_occurrences: int | None
    remaining_minimum: int | None
    remaining_capacity: int | None
    unknown_reason: str | None


class WeeklyNutritionFrequencyProgressRead(BaseModel):
    person_id: uuid.UUID
    as_of_date: date
    week_start: date
    week_end: date
    timezone: str
    guidelines: list[WeeklyFrequencyGuidelineProgressRead]
