import uuid
from datetime import date, datetime, time
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

MealType = Literal["breakfast", "lunch", "snack", "dinner"]
MEAL_TYPES: tuple[MealType, ...] = ("breakfast", "lunch", "snack", "dinner")


class MealPlanParticipantWrite(BaseModel):
    person_id: uuid.UUID
    quantity: Decimal | None = Field(default=None, gt=0)
    unit: str | None = Field(default=None, min_length=1, max_length=24)

    @model_validator(mode="after")
    def validate_quantity_shape(self) -> "MealPlanParticipantWrite":
        if (self.quantity is None) != (self.unit is None):
            raise ValueError("quantity and unit must be provided together.")
        return self


class MealPlanEntryCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    date: date
    meal_type: MealType
    local_time: time
    recipe_id: uuid.UUID
    participants: list[MealPlanParticipantWrite] = Field(min_length=1)
    location: str | None = Field(default=None, max_length=160)
    notes: str | None = Field(default=None, max_length=2000)


class MealPlanEntryUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    date: date | None = None
    meal_type: MealType | None = None
    local_time: time | None = None
    recipe_id: uuid.UUID | None = None
    participants: list[MealPlanParticipantWrite] | None = Field(default=None, min_length=1)
    location: str | None = Field(default=None, max_length=160)
    notes: str | None = Field(default=None, max_length=2000)


class MealPlanParticipantRead(BaseModel):
    person_id: uuid.UUID
    first_name: str
    last_name: str | None
    quantity: Decimal | None
    unit: str | None
    energy_kcal: Decimal | None


class MealPlanEntryRead(BaseModel):
    id: uuid.UUID
    meal_type: MealType
    title: str | None
    scheduled_at: datetime
    local_time: time
    status: str
    recipe_id: uuid.UUID | None
    recipe_name: str | None
    location: str | None
    notes: str | None
    participants: list[MealPlanParticipantRead]


class MealPlanSlotRead(BaseModel):
    meal_type: MealType
    meals: list[MealPlanEntryRead]


class MealPlanDayRead(BaseModel):
    date: date
    slots: list[MealPlanSlotRead]


class FamilyMealPlanRead(BaseModel):
    family_id: uuid.UUID
    family_name: str
    timezone: str
    start_date: date
    end_date: date
    days: list[MealPlanDayRead]
