import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

ShoppingItemStatus = Literal["needed", "purchased"]


class PantryLotCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    food_item_id: uuid.UUID
    quantity_available: Decimal = Field(gt=0)
    unit: str = Field(min_length=1, max_length=24)
    location: str | None = Field(default=None, max_length=80)
    expires_at: datetime | None = None
    notes: str | None = Field(default=None, max_length=2000)


class PantryLotUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    quantity_available: Decimal | None = Field(default=None, gt=0)
    unit: str | None = Field(default=None, min_length=1, max_length=24)
    location: str | None = Field(default=None, max_length=80)
    expires_at: datetime | None = None
    is_available: bool | None = None
    notes: str | None = Field(default=None, max_length=2000)


class PantryLotRead(BaseModel):
    id: uuid.UUID
    family_id: uuid.UUID
    food_item_id: uuid.UUID
    food_item_name: str
    stock_key: str
    quantity_available: Decimal
    unit: str
    location: str | None
    expires_at: datetime | None
    observed_at: datetime
    is_available: bool
    notes: str | None
    created_at: datetime
    updated_at: datetime


class PlannedRequirementRead(BaseModel):
    food_item_id: uuid.UUID
    food_item_name: str
    required_quantity: Decimal
    available_quantity: Decimal
    missing_quantity: Decimal
    unit: str


class ShoppingListItemCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=160)
    quantity: Decimal | None = Field(default=None, gt=0)
    unit: str | None = Field(default=None, min_length=1, max_length=24)
    notes: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_quantity_shape(self) -> "ShoppingListItemCreate":
        if (self.quantity is None) != (self.unit is None):
            raise ValueError("quantity and unit must be provided together.")
        return self


class ShoppingListItemUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=1, max_length=160)
    quantity: Decimal | None = Field(default=None, gt=0)
    unit: str | None = Field(default=None, min_length=1, max_length=24)
    status: ShoppingItemStatus | None = None
    notes: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_quantity_shape(self) -> "ShoppingListItemUpdate":
        fields = self.model_fields_set
        if ("quantity" in fields) != ("unit" in fields):
            raise ValueError("quantity and unit must be updated together.")
        return self


class ShoppingListItemRead(BaseModel):
    id: uuid.UUID
    food_item_id: uuid.UUID | None
    name: str
    quantity: Decimal | None
    unit: str | None
    item_source: Literal["automatic", "manual"]
    status: ShoppingItemStatus
    notes: str | None
    sort_order: int


class ShoppingListRefreshRequest(BaseModel):
    start_date: date
    days: int = Field(default=7, ge=1, le=14)


class ShoppingListRead(BaseModel):
    id: uuid.UUID
    family_id: uuid.UUID
    title: str
    status: Literal["active", "archived"]
    planning_start: date | None
    planning_end: date | None
    generated_at: datetime | None
    requirements: list[PlannedRequirementRead]
    planning_issues: list[str]
    items: list[ShoppingListItemRead]
    created_at: datetime
    updated_at: datetime
