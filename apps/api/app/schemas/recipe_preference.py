import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class RecipeRatingWrite(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    rating: int = Field(ge=1, le=5)
    notes: str | None = Field(default=None, max_length=2000)


class PersonRecipeRatingRead(BaseModel):
    person_id: uuid.UUID
    first_name: str
    last_name: str | None
    rating: int
    notes: str | None
    updated_at: datetime


class RecipePreferenceSummaryRead(BaseModel):
    recipe_id: uuid.UUID
    average_rating: Decimal | None
    rating_count: int
    ratings: list[PersonRecipeRatingRead]
