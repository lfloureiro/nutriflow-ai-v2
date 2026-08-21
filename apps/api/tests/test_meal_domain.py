from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.family import Family
from app.models.meal import MealEvent, MealParticipant, Serving, ServingNutritionComponent
from app.models.person import Person


def test_shared_meal_supports_person_specific_servings(db_session: Session) -> None:
    family = Family(name="Meal Domain Test Family", timezone="Europe/Lisbon")
    first_person = Person(
        family=family,
        first_name="First",
        last_name="Tester",
        birth_date=date(1980, 1, 1),
        preferred_locale="pt-PT",
        timezone="Europe/Lisbon",
    )
    second_person = Person(
        family=family,
        first_name="Second",
        last_name="Tester",
        birth_date=date(1982, 1, 1),
        preferred_locale="pt-PT",
        timezone="Europe/Lisbon",
    )

    dinner = MealEvent(
        family=family,
        meal_type="dinner",
        title="Spaghetti Bolognese",
        scheduled_at=datetime(2026, 8, 21, 19, 30, tzinfo=UTC),
        timezone="Europe/Lisbon",
        status="served",
        served_at=datetime(2026, 8, 21, 19, 35, tzinfo=UTC),
        source="user",
    )

    first_participant = MealParticipant(
        meal_event=dinner,
        person=first_person,
        status="partial",
    )
    second_participant = MealParticipant(
        meal_event=dinner,
        person=second_person,
        status="consumed",
    )

    first_serving = Serving(
        meal_participant=first_participant,
        item_type="dish",
        item_key="spaghetti_bolognese",
        item_name="Spaghetti Bolognese",
        status="partial",
        quantity_planned=Decimal("350.0000"),
        quantity_served=Decimal("350.0000"),
        quantity_consumed=Decimal("300.0000"),
        quantity_unit="g",
        energy_planned_kcal=Decimal("650.00"),
        energy_served_kcal=Decimal("650.00"),
        energy_consumed_kcal=Decimal("560.00"),
        nutrition_source="estimated",
    )
    first_serving.nutrition_components.append(
        ServingNutritionComponent(
            nutrient_key="protein",
            planned_value=Decimal("32.0000"),
            served_value=Decimal("32.0000"),
            consumed_value=Decimal("27.5000"),
            unit="g",
        )
    )

    second_serving = Serving(
        meal_participant=second_participant,
        item_type="dish",
        item_key="spaghetti_bolognese",
        item_name="Spaghetti Bolognese",
        status="consumed",
        quantity_planned=Decimal("250.0000"),
        quantity_served=Decimal("250.0000"),
        quantity_consumed=Decimal("250.0000"),
        quantity_unit="g",
        energy_planned_kcal=Decimal("465.00"),
        energy_served_kcal=Decimal("465.00"),
        energy_consumed_kcal=Decimal("465.00"),
        nutrition_source="estimated",
    )
    second_serving.nutrition_components.append(
        ServingNutritionComponent(
            nutrient_key="protein",
            planned_value=Decimal("23.0000"),
            served_value=Decimal("23.0000"),
            consumed_value=Decimal("23.0000"),
            unit="g",
        )
    )

    db_session.add(family)
    db_session.flush()

    assert dinner.id is not None
    assert first_participant.id is not None
    assert second_participant.id is not None
    assert first_serving.id is not None
    assert second_serving.id is not None

    db_session.expire(dinner, ["participants"])
    assert len(dinner.participants) == 2

    db_session.expire(first_person, ["meal_participations"])
    db_session.expire(second_person, ["meal_participations"])
    assert len(first_person.meal_participations) == 1
    assert len(second_person.meal_participations) == 1

    db_session.expire(first_participant, ["servings"])
    db_session.expire(second_participant, ["servings"])
    assert first_participant.servings[0].quantity_consumed == Decimal("300.0000")
    assert second_participant.servings[0].quantity_consumed == Decimal("250.0000")
    assert first_participant.servings[0].energy_consumed_kcal == Decimal("560.00")
    assert second_participant.servings[0].energy_consumed_kcal == Decimal("465.00")

    db_session.expire(first_serving, ["nutrition_components"])
    assert first_serving.nutrition_components[0].nutrient_key == "protein"
    assert first_serving.nutrition_components[0].consumed_value == Decimal("27.5000")
