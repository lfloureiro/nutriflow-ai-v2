import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

RecommendationDecisionAction = Literal["accepted", "rejected", "modified"]


class RecommendationDecisionCreate(BaseModel):
    action: RecommendationDecisionAction
    scheduled_at: datetime | None = None
    timezone: str | None = Field(default=None, max_length=64)
    quantity: Decimal | None = Field(default=None, gt=0)
    quantity_unit: str | None = Field(default=None, min_length=1, max_length=24)
    meal_type: str | None = Field(default=None, min_length=1, max_length=32)
    title: str | None = Field(default=None, max_length=160)
    location: str | None = Field(default=None, max_length=160)
    notes: str | None = None
    feedback_metadata: dict[str, object] | None = None


class RecommendationDecisionRead(BaseModel):
    feedback_id: uuid.UUID
    recommendation_option_id: uuid.UUID
    action: RecommendationDecisionAction
    resulting_serving_id: uuid.UUID | None
    meal_event_id: uuid.UUID | None
    meal_event_status: str | None
    scheduled_at: datetime | None
    quantity_planned: Decimal | None
    quantity_unit: str | None
    energy_planned_kcal: Decimal | None
