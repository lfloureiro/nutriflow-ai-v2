import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.schemas.external_menu import NutritionEvidenceLevel
from app.schemas.meal_type import MealType
from app.schemas.practical_recommendation import PracticalMealRecommendationRunRead

ExternalRecommendationSourceKind = Literal["restaurant", "delivery"]


class ExternalMealRecommendationCreate(BaseModel):
    scheduled_at: datetime
    meal_type: MealType
    source_kinds: list[ExternalRecommendationSourceKind] = Field(
        default_factory=lambda: ["restaurant", "delivery"],
        min_length=1,
        max_length=2,
    )
    delivery_provider_keys: list[str] = Field(default_factory=list, max_length=20)
    location: str | None = Field(default=None, max_length=255)
    available_minutes: int | None = Field(default=None, ge=0)
    max_candidates: int = Field(default=50, ge=1, le=100)
    max_results: int | None = Field(default=10, ge=1, le=10)

    @field_validator("scheduled_at")
    @classmethod
    def validate_scheduled_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("scheduled_at must be timezone-aware.")
        return value


class ExternalMealCandidateEvidenceRead(BaseModel):
    catalog_key: str
    item_name: str
    merchant_name: str | None
    source_kinds: list[str]
    provider_keys: list[str]
    source_reference: str | None
    composition_id: uuid.UUID | None
    reference_quantity: Decimal | None
    reference_unit: str | None
    nutrition_evidence_level: NutritionEvidenceLevel | None
    nutrition_confidence: Decimal | None
    evaluated: bool
    reason: str | None


class ExternalMealRecommendationRead(BaseModel):
    person_id: uuid.UUID
    planning_date: date
    scheduled_at: datetime
    meal_type: str
    discovered_count: int
    selected_count: int
    evaluated_count: int
    evidence: list[ExternalMealCandidateEvidenceRead]
    recommendation: PracticalMealRecommendationRunRead | None
