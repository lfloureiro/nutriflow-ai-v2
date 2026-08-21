from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.family import Family
from app.models.person import Person


def test_family_person_relationship(db_session: Session) -> None:
    family = Family(
        name="Test Family",
        timezone="Europe/Lisbon",
    )

    person = Person(
        family=family,
        first_name="Test",
        last_name="Person",
        birth_date=date(1990, 1, 1),
        preferred_locale="pt-PT",
        timezone="Europe/Lisbon",
    )

    db_session.add(family)
    db_session.flush()

    assert family.id is not None
    assert person.id is not None
    assert person.family_id == family.id
    assert person in family.persons

    saved_person = db_session.scalar(
        select(Person).where(Person.id == person.id)
    )

    assert saved_person is not None
    assert saved_person.family.id == family.id
    assert saved_person.family.name == "Test Family"

