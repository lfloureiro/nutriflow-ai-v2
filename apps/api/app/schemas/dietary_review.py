import re
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ConditionWrite(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    code: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=160)
    status: Literal["reported", "suspected", "confirmed", "resolved"] = "reported"
    source: Literal["user", "doctor", "nutritionist", "document"] = "user"
    source_reference: str | None = Field(default=None, max_length=500)
    started_on: date | None = None
    ended_on: date | None = None
    notes: str | None = Field(default=None, max_length=5000)

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        value = value.lower()
        if not re.fullmatch(r"[a-z0-9][a-z0-9_.-]*", value):
            raise ValueError("Use a stable code with letters, numbers, dots or hyphens.")
        return value

    @model_validator(mode="after")
    def validate_dates(self):
        if self.started_on and self.ended_on and self.ended_on < self.started_on:
            raise ValueError("End date must not precede start date.")
        if self.status == "confirmed" and self.source == "user":
            raise ValueError("A reported condition is not a professional confirmation.")
        if self.source != "user" and not self.source_reference:
            raise ValueError("Professional/document sources require a reference.")
        return self


class ConditionUpdate(ConditionWrite):
    expected_version: int = Field(gt=0)


class ConditionRead(ConditionWrite):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    person_id: uuid.UUID
    version: int
    created_at: datetime
    updated_at: datetime


class ConditionEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    version: int
    created_at: datetime
    snapshot: dict


class FodmapReferenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    reference_key: str
    name_pt: str
    name_en: str
    classification: str
    fodmap_groups: list[str]
    preparation: str
    evidence_kind: str
    source_name: str
    source_url: str
    source_version: str
    retrieved_on: date
    notes_pt: str
    notes_en: str


class SubstitutionWrite(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    recipe_ingredient_id: uuid.UUID
    replacement_name: str = Field(min_length=1, max_length=160)
    replacement_food_item_id: uuid.UUID | None = None
    reference_id: uuid.UUID | None = None
    replacement_quantity: Decimal | None = Field(
        default=None, gt=0, max_digits=14, decimal_places=4
    )
    replacement_unit: Literal["g", "ml", "un", "serving"] | None = None
    notes: str = Field(default="", max_length=5000)

    @model_validator(mode="after")
    def validate_quantity(self):
        if (self.replacement_quantity is None) != (self.replacement_unit is None):
            raise ValueError("Supply both quantity and unit, or neither.")
        return self


class SubstitutionUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    expected_version: int = Field(gt=0)
    status: Literal["proposed", "reviewed", "rejected"]
    notes: str = Field(max_length=5000)
    replacement_quantity: Decimal | None = Field(
        default=None, gt=0, max_digits=14, decimal_places=4
    )
    replacement_unit: Literal["g", "ml", "un", "serving"] | None = None

    @model_validator(mode="after")
    def validate_quantity_update(self):
        supplied = self.model_fields_set
        if ("replacement_quantity" in supplied) != ("replacement_unit" in supplied):
            raise ValueError("Update quantity and unit together, or omit both.")
        if (self.replacement_quantity is None) != (self.replacement_unit is None):
            raise ValueError("Supply both quantity and unit, or neither.")
        return self


class SubstitutionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    recipe_ingredient_id: uuid.UUID
    replacement_name: str
    replacement_food_item_id: uuid.UUID | None
    replacement_quantity: Decimal | None
    replacement_unit: str | None
    reference_id: uuid.UUID | None
    status: str
    notes: str
    version: int


class ReviewIngredientRead(BaseModel):
    id: uuid.UUID
    food_item_id: uuid.UUID
    name: str
    quantity: Decimal
    unit: str
    references: list[FodmapReferenceRead]
    substitutions: list[SubstitutionRead]


class ReviewRecipeRead(BaseModel):
    id: uuid.UUID
    name: str
    source: str
    serving_count: Decimal | None = None
    active_variants: list[dict] = Field(default_factory=list)
    assessment_status: Literal["not_evaluated"] = "not_evaluated"
    ingredients: list[ReviewIngredientRead]
