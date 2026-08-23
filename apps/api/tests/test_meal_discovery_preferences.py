from sqlalchemy.orm import Session

from app.models.family import Family
from app.models.person import Person
from app.models.person_profile import PersonProfile
from app.services.person import get_person_meal_discovery


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
