import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.schemas.planning_bootstrap import PlanningDailyNutritionStateRead

ConsumptionStatus = Literal["consumed", "partial", "skipped"]


class MealConsumptionUpdate(BaseModel):
    status: ConsumptionStatus
    quantity_consumed: Decimal | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def validate_quantity(self) -> "MealConsumptionUpdate":
        if self.status == "partial" and self.quantity_consumed is None:
            raise ValueError("quantity_consumed is required for partial consumption.")
        if self.status == "skipped" and self.quantity_consumed is not None:
            raise ValueError("A skipped serving cannot have quantity_consumed.")
        return self


class MealConsumptionRead(BaseModel):
    meal_event_id: uuid.UUID
    person_id: uuid.UUID
    serving_id: uuid.UUID
    status: ConsumptionStatus
    quantity_planned: Decimal | None
    quantity_consumed: Decimal | None
    quantity_unit: str | None
    energy_planned_kcal: Decimal | None
    energy_consumed_kcal: Decimal | None
    consumed_at: datetime | None
    daily_nutrition_state: PlanningDailyNutritionStateRead
