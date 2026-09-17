import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.weekly_planning import (
    SharedWeeklyPlanProposalCreate,
    SharedWeeklyPlanProposalRead,
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
from app.services.shared_practical_recommendation_api import SharedPracticalRecommendationApiError
from app.services.weekly_planning_api import WeeklyPlanningApiError, propose_shared_weekly_plan

router = APIRouter(
    prefix="/families/{family_id}/weekly-planning",
    tags=["weekly-planning"],
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
    SharedPracticalRecommendationApiError,
    WeeklyPlanningApiError,
)


@router.post(
    "/proposals",
    response_model=SharedWeeklyPlanProposalRead,
    status_code=status.HTTP_201_CREATED,
)
def create_shared_weekly_plan_proposal_endpoint(
    family_id: uuid.UUID,
    data: SharedWeeklyPlanProposalCreate,
    db: Annotated[Session, Depends(get_db)],
) -> SharedWeeklyPlanProposalRead:
    family = _family_or_404(db, family_id)
    try:
        return propose_shared_weekly_plan(db, family=family, data=data)
    except _NOT_FOUND_ERRORS as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except _DOMAIN_ERRORS as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
