import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.family_meal_plan import (
    FamilyMealPlanRead,
    MealPlanEntryCreate,
    MealPlanEntryRead,
    MealPlanEntryUpdate,
)
from app.schemas.meal_consumption import MealConsumptionRead, MealConsumptionUpdate
from app.services.family import get_family
from app.services.family_meal_plan import (
    MealPlanEntryLockedError,
    MealPlanEntryNotFoundError,
    MealPlanError,
    MealPlanSlotConflictError,
    build_family_meal_plan,
    cancel_meal_plan_entry,
    create_meal_plan_entry,
    update_meal_plan_entry,
)
from app.services.meal_consumption import (
    MealConsumptionError,
    MealConsumptionNotFoundError,
    record_meal_consumption,
    record_participant_meal_consumption,
)

router = APIRouter(prefix="/families/{family_id}/meal-plan", tags=["meal-plan"])


def _require_family(db: Session, family_id: uuid.UUID):
    family = get_family(db, family_id)
    if family is None:
        raise HTTPException(status_code=404, detail="Family not found")
    return family


@router.get("", response_model=FamilyMealPlanRead)
def get_family_meal_plan_endpoint(
    family_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    start_date: date | None = None,
    days: Annotated[int, Query(ge=1, le=14)] = 7,
) -> FamilyMealPlanRead:
    family = _require_family(db, family_id)
    return build_family_meal_plan(db, family, start_date=start_date, day_count=days)


@router.post("", response_model=MealPlanEntryRead, status_code=status.HTTP_201_CREATED)
def create_meal_plan_entry_endpoint(
    family_id: uuid.UUID,
    data: MealPlanEntryCreate,
    db: Annotated[Session, Depends(get_db)],
) -> MealPlanEntryRead:
    family = _require_family(db, family_id)
    try:
        return create_meal_plan_entry(db, family, data)
    except MealPlanSlotConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except MealPlanError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.patch("/{meal_event_id}", response_model=MealPlanEntryRead)
def update_meal_plan_entry_endpoint(
    family_id: uuid.UUID,
    meal_event_id: uuid.UUID,
    data: MealPlanEntryUpdate,
    db: Annotated[Session, Depends(get_db)],
) -> MealPlanEntryRead:
    family = _require_family(db, family_id)
    try:
        return update_meal_plan_entry(db, family, meal_event_id, data)
    except MealPlanEntryNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (MealPlanEntryLockedError, MealPlanSlotConflictError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except MealPlanError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.patch(
    "/{meal_event_id}/participants/{person_id}/servings/{serving_id}/consumption",
    response_model=MealConsumptionRead,
)
def record_meal_consumption_endpoint(
    family_id: uuid.UUID,
    meal_event_id: uuid.UUID,
    person_id: uuid.UUID,
    serving_id: uuid.UUID,
    data: MealConsumptionUpdate,
    db: Annotated[Session, Depends(get_db)],
) -> MealConsumptionRead:
    family = _require_family(db, family_id)
    try:
        return record_meal_consumption(
            db,
            family=family,
            meal_event_id=meal_event_id,
            person_id=person_id,
            serving_id=serving_id,
            data=data,
        )
    except MealConsumptionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except MealConsumptionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.patch(
    "/{meal_event_id}/participants/{person_id}/consumption",
    response_model=MealConsumptionRead,
)
def record_participant_meal_consumption_endpoint(
    family_id: uuid.UUID,
    meal_event_id: uuid.UUID,
    person_id: uuid.UUID,
    data: MealConsumptionUpdate,
    db: Annotated[Session, Depends(get_db)],
) -> MealConsumptionRead:
    family = _require_family(db, family_id)
    try:
        return record_participant_meal_consumption(
            db,
            family=family,
            meal_event_id=meal_event_id,
            person_id=person_id,
            data=data,
        )
    except MealConsumptionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except MealConsumptionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.delete("/{meal_event_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_meal_plan_entry_endpoint(
    family_id: uuid.UUID,
    meal_event_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    _require_family(db, family_id)
    try:
        cancel_meal_plan_entry(db, family_id, meal_event_id)
    except MealPlanEntryNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except MealPlanEntryLockedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)