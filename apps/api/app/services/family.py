import uuid

from sqlalchemy.orm import Session

from app.models.family import Family
from app.schemas.family import FamilyCreate, FamilyUpdate


def create_family(db: Session, data: FamilyCreate) -> Family:
    family = Family(**data.model_dump())
    db.add(family)
    db.commit()
    db.refresh(family)
    return family


def get_family(db: Session, family_id: uuid.UUID) -> Family | None:
    return db.get(Family, family_id)


def update_family(db: Session, family: Family, data: FamilyUpdate) -> Family:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(family, field, value)
    db.commit()
    db.refresh(family)
    return family
