import uuid
from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.meal_plan_fit import MealPlanFitRead
from app.schemas.meal_type import MealType


class VariantOperation(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    recipe_ingredient_id: uuid.UUID
    replacement_food_item_id: uuid.UUID
    quantity: Decimal = Field(gt=0, max_digits=14, decimal_places=4)
    unit: Literal["g", "ml", "un", "serving"]
    preparation: str = Field(default="", max_length=160)


class VariantCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    base_recipe_id: uuid.UUID
    name: str = Field(min_length=1, max_length=100)
    serving_count: Decimal = Field(gt=0, max_digits=8, decimal_places=2)
    operations: list[VariantOperation] = Field(min_length=1, max_length=100)
    revises_variant_id: uuid.UUID | None = None

    @model_validator(mode="after")
    def unique_operations(self):
        ids = [o.recipe_ingredient_id for o in self.operations]
        if len(ids) != len(set(ids)):
            raise ValueError("Each ingredient may be replaced only once in a complete variant.")
        return self


class VariantRead(BaseModel):
    id: uuid.UUID
    base_recipe_id: uuid.UUID
    recipe_id: uuid.UUID
    base_name: str
    name: str
    revision: int
    version: int
    status: str
    serving_count: Decimal | None
    operations: list[dict]
    issues: list[str]
    energy_per_serving: Decimal | None
    confirmation_mode: str = "validated_variant"


class VariantParticipant(BaseModel):
    person_id: uuid.UUID
    quantity: Decimal = Field(default=Decimal(1), gt=0, max_digits=10, decimal_places=4)


class VariantValidationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(gt=0)
    planning_date: date
    meal_type: MealType
    participants: list[VariantParticipant] = Field(min_length=1, max_length=20)

    @model_validator(mode="after")
    def unique_people(self):
        ids = [p.person_id for p in self.participants]
        if len(ids) != len(set(ids)):
            raise ValueError("Each participant must be unique.")
        return self


class VariantParticipantValidation(BaseModel):
    person_id: uuid.UUID
    eligible: bool
    issues: list[str]
    fit: MealPlanFitRead | None


class VariantValidationRead(BaseModel):
    variant_id: uuid.UUID
    eligible: bool
    issues: list[str]
    participants: list[VariantParticipantValidation]


class VariantRetireRequest(BaseModel):
    expected_version: int = Field(gt=0)


class RecipeEditOperation(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    recipe_ingredient_id: uuid.UUID
    replacement_food_item_id: uuid.UUID | None = None
    replacement_name: str = Field(default="", max_length=160)
    quantity: Decimal = Field(gt=0, max_digits=14, decimal_places=4)
    unit: str = Field(min_length=1, max_length=24)
    preparation: str = Field(default="", max_length=160)


class RecipeEditCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    base_recipe_id: uuid.UUID
    name: str = Field(min_length=1, max_length=100)
    serving_count: Decimal | None = Field(default=None, gt=0, max_digits=8, decimal_places=2)
    operations: list[RecipeEditOperation] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def validate_operations(self):
        ids = [operation.recipe_ingredient_id for operation in self.operations]
        if len(ids) != len(set(ids)):
            raise ValueError("Each ingredient may be replaced once.")
        if any(not operation.replacement_food_item_id and not operation.replacement_name for operation in self.operations):
            raise ValueError("A replacement needs an ingredient or an accepted description.")
        return self
