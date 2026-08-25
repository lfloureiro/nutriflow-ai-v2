from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.schemas.external_menu import NutritionEvidenceLevel
from app.schemas.restaurant_discovery import RestaurantDiscoveryPlaceRead


class RestaurantMenuSyncCreate(BaseModel):
    area: str | None = Field(default=None, max_length=255)
    restaurant_limit: int = Field(default=8, ge=1, le=20)
    item_limit_per_restaurant: int = Field(default=60, ge=1, le=100)


class RestaurantMenuItemRead(BaseModel):
    restaurant_place_id: str
    restaurant_name: str
    item_name: str
    description: str | None
    item_price: Decimal | None
    currency: str
    energy_kcal: Decimal | None
    nutrition_evidence_level: NutritionEvidenceLevel | None
    nutrition_confidence: Decimal | None
    nutrition_basis_reference: str | None
    source_reference: str
    catalog_key: str | None
    eligible_for_nutrition_ranking: bool


class RestaurantMenuRead(BaseModel):
    restaurant: RestaurantDiscoveryPlaceRead
    pages_scanned: list[str]
    items: list[RestaurantMenuItemRead]
    error: str | None = None


class RestaurantMenuSyncRead(BaseModel):
    provider: str
    area: str
    observed_at: datetime
    menus: list[RestaurantMenuRead]
    ingested_item_count: int
    nutrition_ready_item_count: int
