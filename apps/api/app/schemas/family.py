import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class FamilyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    timezone: str = Field(default="Europe/Lisbon", max_length=64)


class FamilyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    timezone: str
    created_at: datetime
    updated_at: datetime

