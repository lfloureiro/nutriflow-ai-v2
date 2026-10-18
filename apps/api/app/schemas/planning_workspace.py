import uuid
from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class MealAttendance(BaseModel):
    model_config = ConfigDict(extra="forbid")
    planning_date: date
    meal_type: Literal["breakfast", "lunch", "snack", "dinner"]
    person_ids: list[uuid.UUID] = Field(max_length=20)

    @field_validator("person_ids")
    @classmethod
    def unique_people(cls, value):
        if len(value) != len(set(value)):
            raise ValueError("Duplicate attendees are not allowed")
        if len(value) == 1:
            raise ValueError("Individual meals must currently be planned in the agenda")
        return value


class WeekSetupWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    person_ids: list[uuid.UUID] = Field(min_length=2, max_length=20)
    meal_types: list[Literal["breakfast", "lunch", "snack", "dinner"]] = Field(
        min_length=1,
        max_length=4,
    )
    excluded_food_item_ids: list[uuid.UUID] = Field(default_factory=list, max_length=100)
    meal_sources: dict[
        Literal["breakfast", "lunch", "snack", "dinner"], Literal["home", "delivery", "restaurant"]
    ] = Field(default_factory=dict, max_length=4)
    attendance: list[MealAttendance] = Field(default_factory=list, max_length=28)
    expected_version: int = Field(default=0, ge=0)

    @field_validator("person_ids", "meal_types", "excluded_food_item_ids")
    @classmethod
    def unique_values(cls, value):
        if len(value) != len(set(value)):
            raise ValueError("Duplicate selections are not allowed.")
        return value


class WeekSetupRead(BaseModel):
    week_start: date
    version: int
    person_ids: list[uuid.UUID]
    meal_types: list[str]
    excluded_food_item_ids: list[uuid.UUID]
    meal_sources: dict[
        Literal["breakfast", "lunch", "snack", "dinner"], Literal["home", "delivery", "restaurant"]
    ] = Field(default_factory=dict, max_length=4)
    attendance: list[MealAttendance] = Field(default_factory=list)


class RetailAlternativeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    retailer: str
    name: str
    alternative_group: str
    product_url: str
    pack_quantity: Decimal
    pack_unit: str
    ingredient_summary: str
    nutrition_per_100: dict | None
    evidence_level: str
    observed_price: Decimal | None
    observed_on: date
    notes: str
    applicable_food_item_ids: list[uuid.UUID] = Field(default_factory=list)


class PlanningRestrictionsRequest(BaseModel):
    attendance: list[MealAttendance] = Field(default_factory=list, max_length=28)
    person_ids: list[uuid.UUID] = Field(min_length=1, max_length=20)
    week_start: date
    meal_types: list[Literal["breakfast", "lunch", "snack", "dinner"]] = Field(
        min_length=1, max_length=4
    )


class AutomaticRestrictionSource(BaseModel):
    person_id: uuid.UUID
    source_id: str
    source_kind: Literal["condition", "diet"]
    label: str
    food_item_ids: list[uuid.UUID]
    dates: list[date]
    meal_types: list[str]


class PlanningRestrictionsRead(BaseModel):
    excluded_food_item_ids: list[uuid.UUID]
    attendance: list[MealAttendance] = Field(default_factory=list)
    sources: list[AutomaticRestrictionSource]
    warnings: list[str]
