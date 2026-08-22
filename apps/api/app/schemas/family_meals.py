import uuid
from datetime import date, datetime

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
