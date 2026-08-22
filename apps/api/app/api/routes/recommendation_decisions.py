import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.recommendation_decision import (
    RecommendationDecisionCreate,
    RecommendationDecisionRead,
)
from app.services.recommendation_decision_api import (
    RecommendationDecisionApiError,
    RecommendationDecisionApiNotFoundError,
    create_recommendation_decision,
)
from app.services.recommendation_feedback import RecommendationFeedbackError
from app.services.recommendation_planning import RecommendationPlanningError

router = APIRouter(prefix="/recommendation-options", tags=["recommendation-decisions"])


@router.post(
    "/{option_id}/decision",
    response_model=RecommendationDecisionRead,
    status_code=status.HTTP_201_CREATED,
)
def create_recommendation_decision_endpoint(
    option_id: uuid.UUID,
    data: RecommendationDecisionCreate,
    db: Annotated[Session, Depends(get_db)],
) -> RecommendationDecisionRead:
    try:
        return create_recommendation_decision(db, option_id=option_id, data=data)
    except RecommendationDecisionApiNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (
        RecommendationDecisionApiError,
        RecommendationFeedbackError,
        RecommendationPlanningError,
    ) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
