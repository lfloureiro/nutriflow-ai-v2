import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.meal_recommendation import MealRecommendationCreate, MealRecommendationRunRead
from app.services.meal_recommendation import MealRecommendationError
from app.services.meal_recommendation_api import (
    MealRecommendationApiError,
    MealRecommendationApiNotFoundError,
    create_meal_recommendation,
)

router = APIRouter(
    prefix="/persons/{person_id}/meal-recommendations",
    tags=["meal-recommendations"],
)


@router.post("", response_model=MealRecommendationRunRead, status_code=status.HTTP_201_CREATED)
def create_meal_recommendation_endpoint(
    person_id: uuid.UUID,
    data: MealRecommendationCreate,
    db: Annotated[Session, Depends(get_db)],
) -> MealRecommendationRunRead:
    try:
        return create_meal_recommendation(db, person_id=person_id, data=data)
    except MealRecommendationApiNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (MealRecommendationApiError, MealRecommendationError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
