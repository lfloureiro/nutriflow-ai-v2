import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.family import Family
from app.models.person import Person
from app.schemas.person import PersonCreate
from app.services.person_energy import create_energy_profile


def create_person(
    db: Session,
    family: Family,
    data: PersonCreate,
) -> Person:
    person = Person(
        family_id=family.id,
        first_name=data.first_name,
        last_name=data.last_name,
        birth_date=data.birth_date,
        preferred_locale=data.preferred_locale,
        timezone=data.timezone,
    )

    db.add(person)
    db.flush()
    if data.energy_profile is not None:
        create_energy_profile(db, person=person, data=data.energy_profile)
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
