import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.meal_type import MealType


class RecipeIngredientWrite(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    food_item_id: uuid.UUID
    quantity: Decimal = Field(gt=0)
    unit: str = Field(min_length=1, max_length=24)
    preparation: str | None = Field(default=None, max_length=160)
    notes: str | None = Field(default=None, max_length=2000)


class RecipeCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=4000)
    suitable_meal_types: list[MealType] = Field(
        default_factory=lambda: ["lunch", "dinner"],
        min_length=1,
        max_length=4,
    )
    yield_quantity: Decimal | None = Field(default=None, gt=0)
    yield_unit: str | None = Field(default=None, min_length=1, max_length=24)
    serving_count: Decimal | None = Field(default=None, gt=0)
    ingredients: list[RecipeIngredientWrite] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_yield_shape(self) -> "RecipeCreate":
        if (self.yield_quantity is None) != (self.yield_unit is None):
            raise ValueError("yield_quantity and yield_unit must be provided together.")
        if len(self.suitable_meal_types) != len(set(self.suitable_meal_types)):
            raise ValueError("suitable_meal_types must not contain duplicates.")
        return self


class RecipeUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=4000)
    suitable_meal_types: list[MealType] | None = Field(default=None, min_length=1, max_length=4)
    yield_quantity: Decimal | None = Field(default=None, gt=0)
    yield_unit: str | None = Field(default=None, min_length=1, max_length=24)
    serving_count: Decimal | None = Field(default=None, gt=0)
    ingredients: list[RecipeIngredientWrite] | None = None
    is_active: bool | None = None

    @model_validator(mode="after")
    def validate_meal_types(self) -> "RecipeUpdate":
        if self.suitable_meal_types is not None and len(self.suitable_meal_types) != len(
            set(self.suitable_meal_types)
        ):
            raise ValueError("suitable_meal_types must not contain duplicates.")
        return self


class RecipeIngredientRead(BaseModel):
    id: uuid.UUID
    food_item_id: uuid.UUID
    food_item_name: str
    quantity: Decimal
    unit: str
    preparation: str | None
    notes: str | None
    sort_order: int
    has_nutrition: bool
    has_energy: bool


class RecipeNutrientRead(BaseModel):
    key: str
    total_value: Decimal
    unit: str
    per_serving_value: Decimal | None


class RecipeCompositionRead(BaseModel):
    id: uuid.UUID
    reference_quantity: Decimal
    reference_unit: str
    energy_kcal: Decimal | None
    energy_per_serving_kcal: Decimal | None
    composition_version: str
    calculation_version: str
    computed_at: datetime
    nutrients: list[RecipeNutrientRead]


class RecipeRead(BaseModel):
    id: uuid.UUID
    family_id: uuid.UUID | None
    scope: Literal["shared", "family"]
    editable: bool
    recipe_key: str
    name: str
    description: str | None
    suitable_meal_types: list[MealType]
    yield_quantity: Decimal | None
    yield_unit: str | None
    serving_count: Decimal | None
    source: str
    is_active: bool
    ingredients: list[RecipeIngredientRead]
    latest_composition: RecipeCompositionRead | None
    nutrition_issues: list[str]
    created_at: datetime
    updated_at: datetime
