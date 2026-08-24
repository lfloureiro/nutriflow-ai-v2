from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.external_menu import (
    ExternalMenuItemIngestedRead,
    NutritionEvidenceLevel,
)

MealDeliveryProviderKey = Literal["uber_eats", "glovo", "bolt_food"]


class MealDeliverySyncRequest(BaseModel):
    delivery_address: str | None = Field(default=None, max_length=500)
    query: str | None = Field(default=None, max_length=160)
    limit: int = Field(default=30, ge=1, le=100)


class MealDeliveryMenuItemRead(BaseModel):
    merchant_name: str
    item_name: str
    description: str | None
    item_price: Decimal
    currency: str
    delivery_fee: Decimal | None
    minimum_order: Decimal | None
    source_reference: str
    energy_kcal: Decimal | None
    nutrition_evidence_level: NutritionEvidenceLevel | None
    nutrition_confidence: Decimal | None
    eligible_for_nutrition_ranking: bool


class MealDeliverySyncRead(BaseModel):
    provider_key: MealDeliveryProviderKey
    observed_count: int
    ingested: list[ExternalMenuItemIngestedRead]
    items: list[MealDeliveryMenuItemRead]
