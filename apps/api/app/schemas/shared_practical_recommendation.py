import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.schemas.meal_recommendation import (
    HumanPortionGuidanceRead,
    MealRecommendationCandidateInput,
)
from app.schemas.meal_type import MealType
from app.schemas.practical_recommendation import (
    CommercialOfferRead,
    PracticalSourceKind,
    RecommendationHistoryHint,
)


class SharedPracticalRecommendationCreate(BaseModel):
    person_ids: list[uuid.UUID] = Field(min_length=2, max_length=20)
    planning_date: date
    scheduled_at: datetime
    meal_type: MealType
    candidates: list[MealRecommendationCandidateInput] = Field(min_length=1, max_length=100)
    location: str | None = Field(default=None, max_length=255)
    available_minutes: int | None = Field(default=None, ge=0)
    has_kitchen: bool | None = None
    source_kinds: list[PracticalSourceKind] = Field(min_length=1, max_length=5)
    delivery_provider_keys: list[str] = Field(default_factory=list, max_length=20)
    provisional_history: list[RecommendationHistoryHint] = Field(
        default_factory=list,
        max_length=14,
    )
    auto_size_portions: bool = False
    max_results: int | None = Field(default=None, ge=1, le=10)


class SharedParticipantEvaluationRead(BaseModel):
    person_id: uuid.UUID
    score: Decimal | None
    quantity: Decimal
    quantity_unit: str
    portion_guidance: HumanPortionGuidanceRead | None = None
    energy_kcal: Decimal | None
    explanation: list[str]


class SharedRecommendationOptionRead(BaseModel):
    candidate_key: str
    candidate_name: str
    candidate_kind: str
    eligible: bool
    rank: int | None
    minimum_score: Decimal | None
    average_score: Decimal | None
    exclusion_reasons: list[str]
    participants: list[SharedParticipantEvaluationRead]


class SharedPracticalRecommendationRead(BaseModel):
    family_id: uuid.UUID
    person_ids: list[uuid.UUID]
    planning_date: date
    scheduled_at: datetime
    meal_type: MealType
    engine_version: str
    source_kinds: list[str]
    options: list[SharedRecommendationOptionRead]
    commercial_offers: list[CommercialOfferRead]


class SharedPracticalPlanCreate(SharedPracticalRecommendationCreate):
    candidate_key: str = Field(min_length=1, max_length=160)
    title: str | None = Field(default=None, max_length=255)
    notes: str | None = Field(default=None, max_length=2000)


class SharedPracticalPlanRead(BaseModel):
    meal_event_id: uuid.UUID
    status: str
    candidate_key: str
    person_ids: list[uuid.UUID]
    serving_ids: list[uuid.UUID]
