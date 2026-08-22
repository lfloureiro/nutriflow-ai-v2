import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.practical_recommendation import (
    PracticalMealRecommendationCreate,
    PracticalMealRecommendationRunRead,
)
from app.services.meal_recommendation import MealRecommendationError
from app.services.meal_recommendation_api import (
    MealRecommendationApiError,
    MealRecommendationApiNotFoundError,
)
from app.services.practical_recommendation_api import (
    PracticalRecommendationApiError,
    create_practical_meal_recommendation,
)

router = APIRouter(
    prefix="/persons/{person_id}/meal-recommendations",
    tags=["meal-recommendations"],
)


@router.post(
    "/practical",
    response_model=PracticalMealRecommendationRunRead,
    status_code=status.HTTP_201_CREATED,
)
def create_practical_meal_recommendation_endpoint(
    person_id: uuid.UUID,
    data: PracticalMealRecommendationCreate,
    db: Annotated[Session, Depends(get_db)],
) -> PracticalMealRecommendationRunRead:
    try:
        return create_practical_meal_recommendation(db, person_id=person_id, data=data)
    except MealRecommendationApiNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (
        MealRecommendationApiError,
        MealRecommendationError,
        PracticalRecommendationApiError,
    ) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
