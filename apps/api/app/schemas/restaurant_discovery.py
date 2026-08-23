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


class RestaurantDiscoveryRead(BaseModel):
    provider: str
    area: str
    observed_at: datetime
    cached: bool
    attribution: str
    restaurants: list[RestaurantDiscoveryPlaceRead] = Field(max_length=50)
