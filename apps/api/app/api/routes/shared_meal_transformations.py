import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.shared_meal_transformation import (
    SharedMealTransformationCreate,
    SharedMealTransformationRead,
)
from app.services.meal_transformation import (
    MealTransformationError,
    MealTransformationNotFoundError,
)
from app.services.shared_meal_transformation import propose_shared_meal_transformations

router = APIRouter(
    prefix="/families/{family_id}/meal-transformations",
    tags=["meal-transformations"],
)


@router.post("/proposals", response_model=SharedMealTransformationRead)
def propose_shared_meal_transformations_endpoint(
    family_id: uuid.UUID,
    data: SharedMealTransformationCreate,
    db: Annotated[Session, Depends(get_db)],
) -> SharedMealTransformationRead:
    try:
        return propose_shared_meal_transformations(
            db,
            family_id=family_id,
            data=data,
        )
    except MealTransformationNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except MealTransformationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
