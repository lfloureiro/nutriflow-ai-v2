from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.external_menu import ExternalMenuItemIngestedRead

MealDeliveryProviderKey = Literal["uber_eats", "glovo", "bolt_food"]


class MealDeliverySyncRequest(BaseModel):
    delivery_address: str | None = Field(default=None, max_length=500)
    query: str | None = Field(default=None, max_length=160)
    limit: int = Field(default=30, ge=1, le=100)


class MealDeliverySyncRead(BaseModel):
    provider_key: MealDeliveryProviderKey
    observed_count: int
    ingested: list[ExternalMenuItemIngestedRead]
