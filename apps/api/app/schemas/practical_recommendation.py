import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.meal_recommendation import (
    MealRecommendationCandidateInput,
    MealRecommendationOptionRead,
)
from app.schemas.meal_type import MealType

PracticalSourceKind = Literal["home", "pantry", "restaurant", "delivery", "store"]


class RecommendationHistoryHint(BaseModel):
    plan_date: date
    candidate_key: str = Field(min_length=1, max_length=160)


class PracticalMealRecommendationCreate(BaseModel):
    daily_nutrition_state_id: uuid.UUID
    planning_date: date
    scheduled_at: datetime
    meal_type: MealType | None = None
    candidates: list[MealRecommendationCandidateInput] = Field(min_length=1, max_length=100)
    location: str | None = Field(default=None, max_length=255)
    available_minutes: int | None = Field(default=None, ge=0)
    has_kitchen: bool | None = None
    source_kinds: list[PracticalSourceKind] = Field(
        default_factory=lambda: ["home", "pantry", "restaurant", "delivery"],
        min_length=1,
        max_length=5,
    )
    provisional_history: list[RecommendationHistoryHint] = Field(
        default_factory=list,
        max_length=14,
    )
    max_results: int | None = Field(default=None, ge=1, le=10)


class CommercialOfferRead(BaseModel):
    candidate_key: str
    source_kind: str
    source_key: str
    location: str | None
    offer_key: str
    provider_key: str
    provider_name: str | None
    item_price: Decimal
    currency: str
    delivery_fee: Decimal | None
    minimum_order: Decimal | None
    total_known_price: Decimal
    observed_at: datetime
    source_reference: str | None


class PracticalMealRecommendationRunRead(BaseModel):
    id: uuid.UUID
    person_id: uuid.UUID
    daily_nutrition_state_id: uuid.UUID
    planning_date: date
    meal_type: str | None
    engine_version: str
    scheduled_at: datetime
    location: str | None
    source_kinds: list[str]
    options: list[MealRecommendationOptionRead]
    commercial_offers: list[CommercialOfferRead]
