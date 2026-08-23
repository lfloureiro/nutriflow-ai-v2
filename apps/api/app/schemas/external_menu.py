import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

NutritionEvidenceLevel = Literal["official", "provider", "estimated"]
ExternalMenuSourceKind = Literal["restaurant", "delivery"]


class ExternalMenuNutrientWrite(BaseModel):
    key: str = Field(min_length=1, max_length=120)
    value: Decimal = Field(ge=0)
    unit: str = Field(min_length=1, max_length=24)


class ExternalMenuNutritionWrite(BaseModel):
    evidence_level: NutritionEvidenceLevel
    confidence: Decimal | None = Field(default=None, ge=0, le=1)
    reference_quantity: Decimal = Field(default=Decimal(1), gt=0)
    reference_unit: str = Field(default="serving", min_length=1, max_length=24)
    energy_kcal: Decimal = Field(ge=0)
    nutrients: list[ExternalMenuNutrientWrite] = Field(default_factory=list, max_length=50)


class ExternalMenuItemObservationWrite(BaseModel):
    provider_key: str = Field(min_length=1, max_length=120)
    provider_name: str | None = Field(default=None, max_length=160)
    merchant_key: str = Field(min_length=1, max_length=160)
    merchant_name: str = Field(min_length=1, max_length=160)
    item_key: str = Field(min_length=1, max_length=160)
    item_name: str = Field(min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=2000)
    source_kind: ExternalMenuSourceKind
    location: str | None = Field(default=None, max_length=160)
    item_price: Decimal = Field(ge=0)
    currency: str = Field(min_length=3, max_length=3)
    delivery_fee: Decimal | None = Field(default=None, ge=0)
    minimum_order: Decimal | None = Field(default=None, ge=0)
    observed_at: datetime
    valid_until: datetime | None = None
    source_reference: str = Field(min_length=1, max_length=255)
    nutrition: ExternalMenuNutritionWrite | None = None


class ExternalMenuItemIngestedRead(BaseModel):
    food_item_id: uuid.UUID
    catalog_key: str
    availability_id: uuid.UUID
    offer_id: uuid.UUID
    composition_id: uuid.UUID | None
    eligible_for_nutrition_ranking: bool
