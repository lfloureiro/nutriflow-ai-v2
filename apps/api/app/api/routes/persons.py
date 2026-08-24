import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.person import (
    PersonEnergyProfileRead,
    PersonMealDiscoveryRead,
    PersonMealDiscoveryUpdate,
    PersonRead,
    PersonUpdate,
)
from app.services.person import (
    PersonDiscoveryConfigurationError,
    PersonUpdateError,
    get_person,
    get_person_meal_discovery,
    update_person,
    update_person_meal_discovery,
)
from app.services.person_energy import PersonEnergyProfileError, get_energy_profile

router = APIRouter(prefix="/persons", tags=["persons"])


@router.get("/{person_id}", response_model=PersonRead)
def get_person_endpoint(
    person_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
) -> PersonRead:
    person = get_person(db, person_id)

    if person is None:
        raise HTTPException(status_code=404, detail="Person not found")

    return person


@router.patch("/{person_id}", response_model=PersonRead)
def update_person_endpoint(
    person_id: uuid.UUID,
    data: PersonUpdate,
    db: Annotated[Session, Depends(get_db)],
) -> PersonRead:
    person = get_person(db, person_id)
    if person is None:
        raise HTTPException(status_code=404, detail="Person not found")
    try:
        return update_person(db, person=person, data=data)
    except (PersonUpdateError, PersonEnergyProfileError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/{person_id}/energy-profile", response_model=PersonEnergyProfileRead)
def get_person_energy_profile_endpoint(
    person_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
) -> PersonEnergyProfileRead:
    person = get_person(db, person_id)
    if person is None:
        raise HTTPException(status_code=404, detail="Person not found")
    try:
        return get_energy_profile(db, person=person)
    except PersonEnergyProfileError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{person_id}/meal-discovery", response_model=PersonMealDiscoveryRead)
def get_person_meal_discovery_endpoint(
    person_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
) -> PersonMealDiscoveryRead:
    person = get_person(db, person_id)
    if person is None:
        raise HTTPException(status_code=404, detail="Person not found")
    return get_person_meal_discovery(person)


@router.put("/{person_id}/meal-discovery", response_model=PersonMealDiscoveryRead)
def update_person_meal_discovery_endpoint(
    person_id: uuid.UUID,
    data: PersonMealDiscoveryUpdate,
    db: Annotated[Session, Depends(get_db)],
) -> PersonMealDiscoveryRead:
    person = get_person(db, person_id)
    if person is None:
        raise HTTPException(status_code=404, detail="Person not found")
    try:
        return update_person_meal_discovery(db, person=person, data=data)
    except PersonDiscoveryConfigurationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
