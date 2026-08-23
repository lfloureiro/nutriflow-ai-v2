import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.family import Family
from app.models.person import Person
from app.models.person_profile import PersonProfile
from app.schemas.person import (
    PersonCreate,
    PersonMealDiscoveryRead,
    PersonMealDiscoveryUpdate,
)
from app.services.person_energy import create_energy_profile

DELIVERY_DISCOVERY_SOURCES = frozenset({"uber_eats", "glovo", "bolt_food"})


class PersonDiscoveryConfigurationError(ValueError):
    pass


def _ensure_profile(person: Person) -> PersonProfile:
    if person.profile is None:
        person.profile = PersonProfile(
            measurement_system="metric",
            energy_unit="kcal",
        )
    return person.profile


def _validate_discovery_configuration(
    family: Family,
    *,
    source_override: list[str] | None,
    address_override: str | None,
    area_override: str | None,
) -> None:
    sources = source_override if source_override is not None else family.meal_discovery_sources
    address = address_override if address_override is not None else family.delivery_address
    area = area_override if area_override is not None else family.restaurant_area
    wants_delivery = bool(DELIVERY_DISCOVERY_SOURCES.intersection(sources))
    if wants_delivery and not (address or "").strip():
        raise PersonDiscoveryConfigurationError(
            "A delivery address is required for the selected delivery providers."
        )
    if "restaurants" in sources and not (area or "").strip():
        raise PersonDiscoveryConfigurationError(
            "A restaurant area is required when restaurant discovery is enabled."
        )


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
        _validate_discovery_configuration(
            family,
            source_override=data.meal_discovery.meal_discovery_sources,
            address_override=data.meal_discovery.delivery_address,
            area_override=data.meal_discovery.restaurant_area,
        )
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


def update_person_meal_discovery(
    db: Session,
    *,
    person: Person,
    data: PersonMealDiscoveryUpdate,
) -> PersonMealDiscoveryRead:
    profile = _ensure_profile(person)
    if data.inherit_family_defaults:
        profile.meal_discovery_sources_override = None
        profile.delivery_address_override = None
        profile.restaurant_area_override = None
    else:
        _validate_discovery_configuration(
            person.family,
            source_override=data.meal_discovery_sources,
            address_override=data.delivery_address,
            area_override=data.restaurant_area,
        )
        profile.meal_discovery_sources_override = data.meal_discovery_sources
        profile.delivery_address_override = data.delivery_address
        profile.restaurant_area_override = data.restaurant_area
    db.commit()
    db.refresh(person)
    return get_person_meal_discovery(person)


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
