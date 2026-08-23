import pytest
from sqlalchemy.orm import Session

from app.models.family import Family
from app.models.person import Person
from app.models.person_profile import PersonProfile
from app.schemas.family import FamilyCreate, FamilyUpdate
from app.schemas.person import PersonMealDiscoveryUpdate
from app.services.family import (
    FamilyDiscoveryConfigurationError,
    create_family,
    update_family,
)
from app.services.person import (
    get_person_meal_discovery,
    update_person_meal_discovery,
)


def test_person_inherits_family_meal_discovery_defaults(db_session: Session) -> None:
    family = Family(
        name="Família",
        timezone="Europe/Lisbon",
        meal_discovery_sources=["shared_recipes", "restaurants", "uber_eats"],
        delivery_address="Rua Exemplo, Lisboa",
        restaurant_area="Benfica, Lisboa",
    )
    person = Person(
        family=family,
        first_name="Ana",
        preferred_locale="pt-PT",
        timezone="Europe/Lisbon",
    )
    db_session.add(person)
    db_session.flush()

    discovery = get_person_meal_discovery(person)

    assert discovery.inherits_family_defaults
    assert discovery.meal_discovery_sources == [
        "shared_recipes",
        "restaurants",
        "uber_eats",
    ]
    assert discovery.delivery_address == "Rua Exemplo, Lisboa"
    assert discovery.restaurant_area == "Benfica, Lisboa"


def test_person_can_override_family_meal_discovery(db_session: Session) -> None:
    family = Family(
        name="Família",
        timezone="Europe/Lisbon",
        meal_discovery_sources=["shared_recipes", "restaurants", "uber_eats"],
        delivery_address="Morada da família",
        restaurant_area="Benfica, Lisboa",
    )
    person = Person(
        family=family,
        first_name="Rui",
        preferred_locale="pt-PT",
        timezone="Europe/Lisbon",
        profile=PersonProfile(
            meal_discovery_sources_override=["shared_recipes", "glovo"],
            delivery_address_override="Morada do Rui",
            restaurant_area_override="Alvalade, Lisboa",
            measurement_system="metric",
            energy_unit="kcal",
        ),
    )
    db_session.add(person)
    db_session.flush()

    discovery = get_person_meal_discovery(person)

    assert not discovery.inherits_family_defaults
    assert discovery.meal_discovery_sources == ["shared_recipes", "glovo"]
    assert discovery.delivery_address == "Morada do Rui"
    assert discovery.restaurant_area == "Alvalade, Lisboa"


def test_person_discovery_override_can_be_changed_and_cleared(db_session: Session) -> None:
    family = Family(
        name="Família",
        timezone="Europe/Lisbon",
        meal_discovery_sources=["shared_recipes", "restaurants"],
        restaurant_area="Benfica, Lisboa",
    )
    person = Person(
        family=family,
        first_name="Marta",
        preferred_locale="pt-PT",
        timezone="Europe/Lisbon",
    )
    db_session.add(person)
    db_session.flush()

    custom = update_person_meal_discovery(
        db_session,
        person=person,
        data=PersonMealDiscoveryUpdate(
            inherit_family_defaults=False,
            meal_discovery_sources=["shared_recipes", "glovo"],
            delivery_address="Morada Marta",
            restaurant_area=None,
        ),
    )
    assert not custom.inherits_family_defaults
    assert custom.meal_discovery_sources == ["shared_recipes", "glovo"]
    assert custom.delivery_address == "Morada Marta"

    inherited = update_person_meal_discovery(
        db_session,
        person=person,
        data=PersonMealDiscoveryUpdate(inherit_family_defaults=True),
    )
    assert inherited.inherits_family_defaults
    assert inherited.meal_discovery_sources == ["shared_recipes", "restaurants"]
    assert inherited.restaurant_area == "Benfica, Lisboa"


def test_delivery_source_requires_family_delivery_address(db_session: Session) -> None:
    with pytest.raises(FamilyDiscoveryConfigurationError, match="delivery address"):
        create_family(
            db_session,
            FamilyCreate(
                name="Família",
                timezone="Europe/Lisbon",
                meal_discovery_sources=["shared_recipes", "uber_eats"],
                delivery_address=None,
                restaurant_area=None,
            ),
        )


def test_partial_family_update_cannot_break_restaurant_configuration(
    db_session: Session,
) -> None:
    family = create_family(
        db_session,
        FamilyCreate(
            name="Família",
            timezone="Europe/Lisbon",
            meal_discovery_sources=["shared_recipes", "restaurants"],
            delivery_address=None,
            restaurant_area="Benfica, Lisboa",
        ),
    )

    with pytest.raises(FamilyDiscoveryConfigurationError, match="restaurant area"):
        update_family(
            db_session,
            family,
            FamilyUpdate(restaurant_area=None),
        )
