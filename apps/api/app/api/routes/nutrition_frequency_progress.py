import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.nutrition_frequency_progress import WeeklyNutritionFrequencyProgressRead
from app.services.nutrition_frequency_progress import (
    NutritionFrequencyProgressError,
    get_weekly_nutrition_frequency_progress,
)

router = APIRouter(prefix="/persons", tags=["nutrition-plans"])


@router.get(
    "/{person_id}/nutrition-frequency-progress",
    response_model=WeeklyNutritionFrequencyProgressRead,
)
def get_nutrition_frequency_progress_endpoint(
    person_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    on_date: Annotated[date, Query()],
) -> WeeklyNutritionFrequencyProgressRead:
    try:
        return get_weekly_nutrition_frequency_progress(
            db,
            person_id=person_id,
            on_date=on_date,
        )
    except NutritionFrequencyProgressError as exc:
        if str(exc) == "Person not found.":
            raise HTTPException(status_code=404, detail="Person not found") from exc
        raise HTTPException(status_code=422, detail=str(exc)) from exc
