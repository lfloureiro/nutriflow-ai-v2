import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.timezone import validate_timezone_name

MealDiscoverySource = Literal[
    "shared_recipes",
    "uber_eats",
    "glovo",
    "bolt_food",
    "restaurants",
]


def _unique_sources(values: list[MealDiscoverySource]) -> list[MealDiscoverySource]:
    if len(values) != len(set(values)):
        raise ValueError("meal_discovery_sources cannot contain duplicates.")
    return values


class FamilyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    timezone: str = Field(default="Europe/Lisbon", max_length=64)
    meal_discovery_sources: list[MealDiscoverySource] = Field(
        default_factory=lambda: ["shared_recipes"],
        min_length=1,
        max_length=5,
    )
    delivery_address: str | None = Field(default=None, max_length=500)
    restaurant_area: str | None = Field(default=None, max_length=255)

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        return validate_timezone_name(value)

    @field_validator("meal_discovery_sources")
    @classmethod
    def validate_sources(cls, values: list[MealDiscoverySource]) -> list[MealDiscoverySource]:
        return _unique_sources(values)


class FamilyUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    timezone: str | None = Field(default=None, max_length=64)
    meal_discovery_sources: list[MealDiscoverySource] | None = Field(
        default=None,
        min_length=1,
        max_length=5,
    )
    delivery_address: str | None = Field(default=None, max_length=500)
    restaurant_area: str | None = Field(default=None, max_length=255)

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str | None) -> str | None:
        return None if value is None else validate_timezone_name(value)

    @field_validator("meal_discovery_sources")
    @classmethod
    def validate_sources(
        cls,
        values: list[MealDiscoverySource] | None,
    ) -> list[MealDiscoverySource] | None:
        return None if values is None else _unique_sources(values)


class FamilyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    timezone: str
    meal_discovery_sources: list[MealDiscoverySource]
    delivery_address: str | None
    restaurant_area: str | None
    created_at: datetime
    updated_at: datetime
