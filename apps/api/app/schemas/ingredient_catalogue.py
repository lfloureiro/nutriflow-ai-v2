import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class IngredientNutrientWrite(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    key: str = Field(min_length=1, max_length=120)
    value: Decimal = Field(ge=0)
    unit: str = Field(min_length=1, max_length=24)


class IngredientCompositionWrite(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    reference_quantity: Decimal = Field(gt=0)
    reference_unit: str = Field(min_length=1, max_length=24)
    energy_kcal: Decimal | None = Field(default=None, ge=0)
    nutrients: list[IngredientNutrientWrite] = Field(default_factory=list)
    notes: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_unique_nutrients(self) -> "IngredientCompositionWrite":
        keys = [nutrient.key.casefold() for nutrient in self.nutrients]
        if len(keys) != len(set(keys)):
            raise ValueError("Nutrient keys must be unique within one composition.")
        return self


class IngredientCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=160)
    brand: str | None = Field(default=None, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    composition: IngredientCompositionWrite | None = None


class IngredientUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=1, max_length=160)
    brand: str | None = Field(default=None, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    is_active: bool | None = None
    composition: IngredientCompositionWrite | None = None


class IngredientNutrientRead(BaseModel):
    key: str
    value: Decimal
    unit: str


class IngredientCompositionRead(BaseModel):
    id: uuid.UUID
    reference_quantity: Decimal
    reference_unit: str
    energy_kcal: Decimal | None
    data_version: str
    source: str
    source_reference: str | None
    effective_at: datetime
    notes: str | None
    nutrients: list[IngredientNutrientRead]


class IngredientRead(BaseModel):
    id: uuid.UUID
    family_id: uuid.UUID | None
    scope: Literal["shared", "family"]
    editable: bool
    catalog_key: str
    name: str
    brand: str | None
    description: str | None
    source: str
    is_active: bool
    recipe_usage_count: int
    latest_composition: IngredientCompositionRead | None
    created_at: datetime
    updated_at: datetime
