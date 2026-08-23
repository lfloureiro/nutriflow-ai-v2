import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.family import MealDiscoverySource

ActivityLevel = Literal["sedentary", "light", "moderate", "active", "very_active"]
EnergyCalculationSex = Literal["male", "female"]
NutritionGoalType = Literal["maintain", "lose", "gain"]


class PersonEnergyProfileCreate(BaseModel):
    sex_for_energy_calculation: EnergyCalculationSex
    height_cm: Decimal = Field(gt=0, le=250)
    weight_kg: Decimal = Field(gt=0, le=500)
    activity_level: ActivityLevel
    goal_type: NutritionGoalType = "maintain"
    target_rate_kg_per_week: Decimal | None = Field(default=None, gt=0, le=1)
    standard_breakfast_kcal: Decimal = Field(default=Decimal(350), ge=0, le=1000)

    @model_validator(mode="after")
    def validate_goal_rate(self) -> "PersonEnergyProfileCreate":
        if self.goal_type in {"lose", "gain"} and self.target_rate_kg_per_week is None:
            raise ValueError("target_rate_kg_per_week is required for lose or gain goals.")
        return self


class PersonMealDiscoveryCreate(BaseModel):
    meal_discovery_sources: list[MealDiscoverySource] | None = Field(
        default=None,
        min_length=1,
        max_length=4,
    )
    delivery_address: str | None = Field(default=None, max_length=500)
    restaurant_area: str | None = Field(default=None, max_length=255)

    @field_validator("meal_discovery_sources")
    @classmethod
    def validate_sources(
        cls,
        values: list[MealDiscoverySource] | None,
    ) -> list[MealDiscoverySource] | None:
        if values is not None and len(values) != len(set(values)):
            raise ValueError("meal_discovery_sources cannot contain duplicates.")
        return values


class PersonCreate(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    birth_date: date | None = None
    preferred_locale: str = Field(default="pt-PT", max_length=16)
    timezone: str = Field(default="Europe/Lisbon", max_length=64)
    energy_profile: PersonEnergyProfileCreate | None = None
    meal_discovery: PersonMealDiscoveryCreate | None = None

    @model_validator(mode="after")
    def validate_energy_birth_date(self) -> "PersonCreate":
        if self.energy_profile is not None and self.birth_date is None:
            raise ValueError("birth_date is required when an energy profile is provided.")
        return self


class PersonRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    family_id: uuid.UUID
    first_name: str
    last_name: str | None
    birth_date: date | None
    preferred_locale: str
    timezone: str
    created_at: datetime
    updated_at: datetime


class PersonMealDiscoveryRead(BaseModel):
    person_id: uuid.UUID
    inherits_family_defaults: bool
    meal_discovery_sources: list[MealDiscoverySource]
    delivery_address: str | None
    restaurant_area: str | None


class PersonEnergyProfileRead(BaseModel):
    person_id: uuid.UUID
    sex_for_energy_calculation: str
    activity_level: str
    standard_breakfast_kcal: Decimal
    height_cm: Decimal
    weight_kg: Decimal
    goal_type: str
    target_rate_kg_per_week: Decimal | None
    estimated_bmr_kcal: Decimal
    estimated_tdee_kcal: Decimal
    energy_min_kcal: Decimal
    energy_max_kcal: Decimal
    calculation_version: str
