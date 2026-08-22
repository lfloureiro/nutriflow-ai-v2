import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel


class FamilyMealParticipantRead(BaseModel):
    person_id: uuid.UUID
    first_name: str
    last_name: str | None
    status: str


class FamilyMealRead(BaseModel):
    id: uuid.UUID
    meal_type: str
    title: str | None
    scheduled_at: datetime
    timezone: str
    status: str
    location: str | None
    participants: list[FamilyMealParticipantRead]


class FamilyMealsDayRead(BaseModel):
    date: date
    meals: list[FamilyMealRead]


class FamilyMealsRead(BaseModel):
    family_id: uuid.UUID
    family_name: str
    timezone: str
    start_date: date
    end_date: date
    days: list[FamilyMealsDayRead]


class FamilyMealServingRead(BaseModel):
    id: uuid.UUID
    item_type: str
    item_name: str
    status: str
    quantity_planned: Decimal | None
    quantity_served: Decimal | None
    quantity_consumed: Decimal | None
    quantity_unit: str | None
    energy_planned_kcal: Decimal | None
    energy_served_kcal: Decimal | None
    energy_consumed_kcal: Decimal | None


class FamilyMealDetailParticipantRead(FamilyMealParticipantRead):
    servings: list[FamilyMealServingRead]


class FamilyMealDetailRead(BaseModel):
    family_id: uuid.UUID
    family_name: str
    timezone: str
    id: uuid.UUID
    meal_type: str
    title: str | None
    scheduled_at: datetime
    status: str
    location: str | None
    participants: list[FamilyMealDetailParticipantRead]
