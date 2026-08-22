import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.planning_bootstrap import PlanningBootstrapRead
from app.services.planning_bootstrap_api import (
    PlanningBootstrapApiError,
    PlanningBootstrapApiNotFoundError,
    get_planning_bootstrap,
)

router = APIRouter(prefix="/persons", tags=["planning-bootstrap"])


@router.get("/{person_id}/planning-bootstrap", response_model=PlanningBootstrapRead)
def get_planning_bootstrap_endpoint(
    person_id: uuid.UUID,
    scheduled_at: Annotated[datetime, Query()],
    db: Annotated[Session, Depends(get_db)],
) -> PlanningBootstrapRead:
    try:
        return get_planning_bootstrap(
            db,
            person_id=person_id,
            scheduled_at=scheduled_at,
        )
    except PlanningBootstrapApiNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PlanningBootstrapApiError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
