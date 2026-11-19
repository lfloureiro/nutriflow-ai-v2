import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.meal_type import MealType


class PartialSwap(BaseModel):
    model_config = ConfigDict(extra="forbid")
    recipe_ingredient_id: uuid.UUID
    replacement_food_item_id: uuid.UUID | None = None
    replacement_name: str = Field(default="", max_length=160)
    quantity: str = Field(default="", max_length=32)
    unit: str = Field(default="", max_length=24)
    preparation: str = Field(default="", max_length=160)


class DraftPortion(BaseModel):
    person_id: uuid.UUID
    quantity: str = Field(default="", max_length=32)
    unit: str = Field(default="serving", max_length=24)


class AdaptationDraftWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    base_recipe_id: uuid.UUID
    meal_event_id: uuid.UUID | None = None
    planning_date: date
    meal_type: MealType
    name: str = Field(min_length=1, max_length=100)
    serving_count: str = Field(default="", max_length=32)
    operations: list[PartialSwap] = Field(max_length=100)
    participants: list[DraftPortion] = Field(min_length=1, max_length=20)
    decisions: dict[uuid.UUID, Literal["accepted", "ignored", "manual"]] = Field(default_factory=dict)

    @model_validator(mode="after")
    def unique_references(self):
        for ids in ([op.recipe_ingredient_id for op in self.operations], [p.person_id for p in self.participants]):
            if len(ids) != len(set(ids)):
                raise ValueError("Draft references must be unique")
        return self


class AdaptationDraftUpdate(AdaptationDraftWrite):
    expected_version: int = Field(gt=0)


class AdaptationDraftRead(BaseModel):
    id: uuid.UUID
    version: int
    status: Literal["draft"] = "draft"
    base_changed: bool
    snapshot: AdaptationDraftWrite
    updated_at: datetime
