import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class PersonCreate(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    birth_date: date | None = None
    preferred_locale: str = Field(default="pt-PT", max_length=16)
    timezone: str = Field(default="Europe/Lisbon", max_length=64)


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

