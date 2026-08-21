import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.family import Family
from app.models.person import Person
from app.schemas.person import PersonCreate


def create_person(
    db: Session,
    family: Family,
    data: PersonCreate,
) -> Person:
    person = Person(
        family_id=family.id,
        **data.model_dump(),
    )

    db.add(person)
    db.commit()
    db.refresh(person)
    return person


def get_person(db: Session, person_id: uuid.UUID) -> Person | None:
    return db.get(Person, person_id)


def list_family_persons(
    db: Session,
    family_id: uuid.UUID,
) -> list[Person]:
    statement = (
        select(Person)
        .where(Person.family_id == family_id)
        .order_by(Person.first_name, Person.last_name)
    )

    return list(db.scalars(statement).all())

