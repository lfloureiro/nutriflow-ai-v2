import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.family import Family
from app.models.person import Person
from app.models.person_profile import PersonProfile
from app.schemas.person import PersonCreate, PersonMealDiscoveryRead
from app.services.person_energy import create_energy_profile


def _ensure_profile(person: Person) -> PersonProfile:
    if person.profile is None:
        person.profile = PersonProfile(
            measurement_system="metric",
            energy_unit="kcal",
        )
    return person.profile


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
    if data.meal_discovery is not None:
        profile = _ensure_profile(person)
        profile.meal_discovery_sources_override = data.meal_discovery.meal_discovery_sources
        profile.delivery_address_override = data.meal_discovery.delivery_address
        profile.restaurant_area_override = data.meal_discovery.restaurant_area
    db.commit()
    db.refresh(person)
    return person


def get_person(db: Session, person_id: uuid.UUID) -> Person | None:
    return db.get(Person, person_id)


def get_person_meal_discovery(person: Person) -> PersonMealDiscoveryRead:
    profile = person.profile
    source_override = None if profile is None else profile.meal_discovery_sources_override
    address_override = None if profile is None else profile.delivery_address_override
    area_override = None if profile is None else profile.restaurant_area_override
    has_override = any(
        value is not None for value in (source_override, address_override, area_override)
    )
    return PersonMealDiscoveryRead(
        person_id=person.id,
        inherits_family_defaults=not has_override,
        meal_discovery_sources=(
            source_override
            if source_override is not None
            else person.family.meal_discovery_sources
        ),
        delivery_address=(
            address_override if address_override is not None else person.family.delivery_address
        ),
        restaurant_area=(
            area_override if area_override is not None else person.family.restaurant_area
        ),
    )


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
