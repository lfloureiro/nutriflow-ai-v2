from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class RestaurantDiscoveryPlaceRead(BaseModel):
    provider_place_id: str
    name: str
    cuisine: list[str]
    amenity: str
    address: str | None
    latitude: Decimal
    longitude: Decimal
    website: str | None
    phone: str | None
    opening_hours: str | None
    source_reference: str
    primary_type: str | None = None
    rating: Decimal | None = None
    rating_count: int | None = None
    price_level: str | None = None
    delivery: bool | None = None
    takeout: bool | None = None
    dine_in: bool | None = None
    serves_lunch: bool | None = None
    serves_dinner: bool | None = None
    serves_vegetarian_food: bool | None = None
    quality_score: Decimal | None = None


class RestaurantDiscoveryRead(BaseModel):
    provider: str
    area: str
    observed_at: datetime
    cached: bool
    attribution: str
    restaurants: list[RestaurantDiscoveryPlaceRead] = Field(max_length=50)
