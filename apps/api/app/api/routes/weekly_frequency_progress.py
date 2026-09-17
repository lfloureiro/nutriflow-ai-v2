import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.weekly_frequency_progress import WeeklyFrequencyProgressRead
from app.services.weekly_frequency_progress import (
    WeeklyFrequencyProgressError,
    get_weekly_frequency_progress,
)

router = APIRouter(prefix="/persons", tags=["nutrition-plans"])


@router.get(
    "/{person_id}/weekly-frequency-progress",
    response_model=WeeklyFrequencyProgressRead,
)
def get_weekly_frequency_progress_endpoint(
    person_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    on_date: Annotated[date, Query()],
) -> WeeklyFrequencyProgressRead:
    try:
        return get_weekly_frequency_progress(
            db,
            person_id=person_id,
            anchor_date=on_date,
        )
    except WeeklyFrequencyProgressError as exc:
        if str(exc) == "Person not found.":
            raise HTTPException(status_code=404, detail="Person not found") from exc
        raise HTTPException(status_code=422, detail=str(exc)) from exc
