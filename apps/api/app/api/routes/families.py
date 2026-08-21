import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.family import FamilyCreate, FamilyRead
from app.schemas.person import PersonCreate, PersonRead
from app.services.family import create_family, get_family
from app.services.person import create_person, list_family_persons

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

    return create_person(db, family, data)


@router.get("/{family_id}/persons", response_model=list[PersonRead])
def list_family_persons_endpoint(
    family_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
) -> list[PersonRead]:
    family = get_family(db, family_id)

    if family is None:
        raise HTTPException(status_code=404, detail="Family not found")

    return list_family_persons(db, family_id)
