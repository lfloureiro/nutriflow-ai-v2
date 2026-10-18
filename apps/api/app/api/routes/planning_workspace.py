import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.planning_workspace import (
    PlanningRestrictionsRead,
    PlanningRestrictionsRequest,
    RetailAlternativeRead,
    WeekSetupRead,
    WeekSetupWrite,
)
from app.services.planning_restrictions import planning_restrictions
from app.services.planning_workspace import get_setup, retail_alternatives, save_setup

router = APIRouter(prefix="/families/{family_id}", tags=["planning workspace"])
DB = Annotated[Session, Depends(get_db)]


@router.post("/planning-restrictions", response_model=PlanningRestrictionsRead)
def read_restrictions(family_id: uuid.UUID, data: PlanningRestrictionsRequest, db: DB):
    return planning_restrictions(db, family_id, data)


@router.get("/planning-setup/{week_start}", response_model=WeekSetupRead | None)
def read_setup(family_id: uuid.UUID, week_start: date, db: DB):
    return get_setup(db, family_id, week_start)


@router.put("/planning-setup/{week_start}", response_model=WeekSetupRead)
def write_setup(family_id: uuid.UUID, week_start: date, data: WeekSetupWrite, db: DB):
    return save_setup(db, family_id, week_start, data)


@router.get("/retail-alternatives", response_model=list[RetailAlternativeRead])
def list_alternatives(family_id: uuid.UUID, db: DB):
    return retail_alternatives(db, family_id)
