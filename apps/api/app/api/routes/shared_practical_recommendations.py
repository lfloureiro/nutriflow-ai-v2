import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.shared_practical_recommendation import (
    SharedPracticalPlanCreate,
    SharedPracticalPlanRead,
    SharedPracticalRecommendationCreate,
    SharedPracticalRecommendationRead,
)
from app.services.commercial_availability import CommercialAvailabilityError
from app.services.family import get_family
from app.services.meal_recommendation_api import (
    MealRecommendationApiError,
    MealRecommendationApiNotFoundError,
)
from app.services.pantry_planning import PantryPlanningError
from app.services.persisted_practical_availability import PersistedPracticalAvailabilityError
from app.services.planning_bootstrap_api import (
    PlanningBootstrapApiError,
    PlanningBootstrapApiNotFoundError,
)
from app.services.recommendation_practical_context import PracticalRecommendationError
from app.services.shared_family_meal import SharedFamilyMealError
from app.services.shared_family_meal_planning import SharedFamilyMealPlanningError
from app.services.shared_practical_recommendation_api import (
    SharedPracticalRecommendationApiError,
    create_shared_practical_recommendation,
    plan_shared_practical_recommendation,
)

router = APIRouter(
    prefix="/families/{family_id}/meal-recommendations/shared-practical",
    tags=["shared-practical-recommendations"],
)


def _family_or_404(db: Session, family_id: uuid.UUID):
    family = get_family(db, family_id)
    if family is None:
        raise HTTPException(status_code=404, detail="Family not found")
    return family


_NOT_FOUND_ERRORS = (
    MealRecommendationApiNotFoundError,
    PlanningBootstrapApiNotFoundError,
)

_DOMAIN_ERRORS = (
    CommercialAvailabilityError,
    MealRecommendationApiError,
    PantryPlanningError,
    PersistedPracticalAvailabilityError,
    PlanningBootstrapApiError,
    PracticalRecommendationError,
    SharedFamilyMealError,
    SharedFamilyMealPlanningError,
    SharedPracticalRecommendationApiError,
)


@router.post(
    "",
    response_model=SharedPracticalRecommendationRead,
    status_code=status.HTTP_201_CREATED,
)
def create_shared_practical_recommendation_endpoint(
    family_id: uuid.UUID,
    data: SharedPracticalRecommendationCreate,
    db: Annotated[Session, Depends(get_db)],
) -> SharedPracticalRecommendationRead:
    family = _family_or_404(db, family_id)
    try:
        return create_shared_practical_recommendation(db, family=family, data=data)
    except _NOT_FOUND_ERRORS as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except _DOMAIN_ERRORS as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post(
    "/plan",
    response_model=SharedPracticalPlanRead,
    status_code=status.HTTP_201_CREATED,
)
def plan_shared_practical_recommendation_endpoint(
    family_id: uuid.UUID,
    data: SharedPracticalPlanCreate,
    db: Annotated[Session, Depends(get_db)],
) -> SharedPracticalPlanRead:
    family = _family_or_404(db, family_id)
    try:
        return plan_shared_practical_recommendation(db, family=family, data=data)
    except _NOT_FOUND_ERRORS as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except _DOMAIN_ERRORS as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
