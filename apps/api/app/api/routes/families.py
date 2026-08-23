import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.family import FamilyCreate, FamilyRead, FamilyUpdate
from app.schemas.family_dashboard import FamilyDashboardRead
from app.schemas.family_meals import FamilyMealsRead
from app.schemas.person import PersonCreate, PersonRead
from app.services.family import create_family, get_family, update_family
from app.services.family_dashboard import build_family_dashboard
from app.services.family_meals import build_family_meals
from app.services.person import create_person, list_family_persons
from app.services.person_energy import PersonEnergyProfileError

router = APIRouter(prefix="/families", tags=["families"])


@router.post("", response_model=FamilyRead, status_code=status.HTTP_201_CREATED)
def create_family_endpoint(
    data: FamilyCreate,
    db: Annotated[Session, Depends(get_db)],
) -> FamilyRead:
    return create_family(db, data)


@router.get("/{family_id}", response_model=FamilyRead)
def get_family_endpoint(
    family_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
) -> FamilyRead:
    family = get_family(db, family_id)

    if family is None:
        raise HTTPException(status_code=404, detail="Family not found")

    return family


@router.patch("/{family_id}", response_model=FamilyRead)
def update_family_endpoint(
    family_id: uuid.UUID,
    data: FamilyUpdate,
    db: Annotated[Session, Depends(get_db)],
) -> FamilyRead:
    family = get_family(db, family_id)
    if family is None:
        raise HTTPException(status_code=404, detail="Family not found")
    return update_family(db, family, data)


@router.get("/{family_id}/dashboard", response_model=FamilyDashboardRead)
def get_family_dashboard_endpoint(
    family_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    on_date: date | None = None,
) -> FamilyDashboardRead:
    family = get_family(db, family_id)

    if family is None:
        raise HTTPException(status_code=404, detail="Family not found")

    return build_family_dashboard(db, family, on_date=on_date)


@router.get("/{family_id}/meals", response_model=FamilyMealsRead)
def get_family_meals_endpoint(
    family_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    start_date: date | None = None,
    days: Annotated[int, Query(ge=1, le=14)] = 7,
) -> FamilyMealsRead:
    family = get_family(db, family_id)

    if family is None:
        raise HTTPException(status_code=404, detail="Family not found")

    return build_family_meals(db, family, start_date=start_date, day_count=days)


@router.post(
    "/{family_id}/persons",
    response_model=PersonRead,
    status_code=status.HTTP_201_CREATED,
)
def create_person_endpoint(
    family_id: uuid.UUID,
    data: PersonCreate,
    db: Annotated[Session, Depends(get_db)],
) -> PersonRead:
    family = get_family(db, family_id)

    if family is None:
        raise HTTPException(status_code=404, detail="Family not found")

    try:
        return create_person(db, family, data)
    except PersonEnergyProfileError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/{family_id}/persons", response_model=list[PersonRead])
def list_family_persons_endpoint(
    family_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
) -> list[PersonRead]:
    family = get_family(db, family_id)

    if family is None:
        raise HTTPException(status_code=404, detail="Family not found")

    return list_family_persons(db, family_id)
