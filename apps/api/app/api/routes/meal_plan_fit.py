import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.meal_plan_fit import MealPlanFitCreate, MealPlanFitRead
from app.services.meal_plan_fit import MealPlanFitError, MealPlanFitNotFoundError
from app.services.meal_plan_fit_weekly_frequency import (
    evaluate_meal_plan_fit_with_weekly_frequency,
)

router = APIRouter(prefix="/persons", tags=["meal-plan-fit"])


@router.post("/{person_id}/meal-plan-fit", response_model=MealPlanFitRead)
def evaluate_meal_plan_fit_endpoint(
    person_id: uuid.UUID,
    data: MealPlanFitCreate,
    db: Annotated[Session, Depends(get_db)],
) -> MealPlanFitRead:
    try:
        return evaluate_meal_plan_fit_with_weekly_frequency(
            db,
            person_id=person_id,
            data=data,
        )
    except MealPlanFitNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except MealPlanFitError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc