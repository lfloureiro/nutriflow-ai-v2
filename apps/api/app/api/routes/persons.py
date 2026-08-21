import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.person import PersonRead
from app.services.person import get_person


router = APIRouter(prefix="/persons", tags=["persons"])


@router.get("/{person_id}", response_model=PersonRead)
def get_person_endpoint(
    person_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> PersonRead:
    person = get_person(db, person_id)

    if person is None:
        raise HTTPException(status_code=404, detail="Person not found")

    return person

