import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.meal_transformation import MealTransformationCreate, MealTransformationRead
from app.services.meal_transformation import (
    MealTransformationError,
    MealTransformationNotFoundError,
    propose_meal_transformations,
)

router = APIRouter(prefix="/persons/{person_id}/meal-transformations", tags=["meal-transformations"])


@router.post("/proposals", response_model=MealTransformationRead)
def propose_meal_transformations_endpoint(
    person_id: uuid.UUID,
    data: MealTransformationCreate,
    db: Annotated[Session, Depends(get_db)],
) -> MealTransformationRead:
    try:
        return propose_meal_transformations(db, person_id=person_id, data=data)
    except MealTransformationNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except MealTransformationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
