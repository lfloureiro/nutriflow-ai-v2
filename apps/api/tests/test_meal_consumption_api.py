import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.main import app
from app.models.family import Family
from app.models.food_catalog import FoodCompositionSnapshot, FoodItem
from app.models.meal import MealEvent, MealParticipant, Serving
from app.models.nutrition_target import NutritionTarget
from app.models.person import Person
from app.services.planning_bootstrap_api import get_planning_bootstrap

PLAN_DATE = "2026-08-23"


def _override_db(db_session: Session):
    def override_get_db():
        yield db_session

    return override_get_db


def _request(db_session: Session, method: str, path: str, **kwargs):
    app.dependency_overrides[get_db] = _override_db(db_session)
    try:
        with TestClient(app) as client:
            return client.request(method, path, **kwargs)
    finally:
        app.dependency_overrides.clear()


def _recipe(db_session: Session, family: Family, meal_type: str) -> str:
    ingredient = FoodItem(
        family=family,
        catalog_key=f"test:consumption:{uuid.uuid4()}",
        name="Base da receita",
        food_kind="ingredient",
        source="test",
        is_active=True,
    )
    ingredient.compositions.append(
        FoodCompositionSnapshot(
            reference_quantity=Decimal(100),
            reference_unit="g",
            energy_kcal=Decimal(100),
            data_version="test-v1",
            source="test",
            effective_at=datetime(2026, 8, 23, tzinfo=UTC),
        )
    )
    db_session.add(ingredient)
    db_session.flush()
    response = _request(
        db_session,
        "POST",
        f"/api/families/{family.id}/recipes",
        json={
            "name": "Receita consumo",
            "suitable_meal_types": [meal_type],
            "serving_count": "4",
            "yield_quantity": "1000",
            "yield_unit": "g",
            "ingredients": [
                {"food_item_id": str(ingredient.id), "quantity": "1000", "unit": "g"}
            ],
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def _setup(db_session: Session, meal_type: str, local_time: str):
    family = Family(name="Consumption family", timezone="Europe/Lisbon")
    person = Person(
        family=family,
        first_name="Ana",
        preferred_locale="pt-PT",
        timezone="Europe/Lisbon",
    )
    target = NutritionTarget(
        person=person,
        valid_from=date(2026, 1, 1),
        energy_min_kcal=Decimal(1800),
        energy_max_kcal=Decimal(2000),
        calculation_version="test-target-v1",
        status="active",
        source="test",
    )
    db_session.add_all([family, target])
    db_session.flush()
    recipe_id = _recipe(db_session, family, meal_type)
    created = _request(
        db_session,
        "POST",
        f"/api/families/{family.id}/meal-plan",
        json={
            "date": PLAN_DATE,
            "meal_type": meal_type,
            "local_time": local_time,
            "recipe_id": recipe_id,
            "participants": [
                {"person_id": str(person.id), "quantity": "400", "unit": "g"}
            ],
        },
    )
    assert created.status_code == 201
    entry = created.json()
    participant = entry["participants"][0]
    assert participant["serving_id"] is not None
    return family, person, entry, participant


def _setup_legacy_without_serving(db_session: Session, meal_type: str):
    family = Family(name=f"Legacy {meal_type} family", timezone="Europe/Lisbon")
    person = Person(
        family=family,
        first_name="Ana",
        preferred_locale="pt-PT",
        timezone="Europe/Lisbon",
    )
    target = NutritionTarget(
        person=person,
        valid_from=date(2026, 1, 1),
        energy_min_kcal=Decimal(1800),
        energy_max_kcal=Decimal(2000),
        calculation_version="test-target-v1",
        status="active",
        source="test",
    )
    event = MealEvent(
        family=family,
        meal_type=meal_type,
        title="Pequeno-almoço" if meal_type == "breakfast" else "Almoço legado",
        scheduled_at=datetime(2026, 8, 23, 8 if meal_type == "breakfast" else 13, 30, tzinfo=ZoneInfo("Europe/Lisbon")),
        timezone="Europe/Lisbon",
        status="planned",
        source="test",
    )
    participant = MealParticipant(
        meal_event=event,
        person=person,
        status="planned",
    )
    db_session.add_all([family, target, event, participant])
    db_session.flush()
    assert participant.servings == []
    return family, person, event, participant


def _consumption_path(family, person, entry, participant) -> str:
    return (
        f"/api/families/{family.id}/meal-plan/{entry['id']}/participants/"
        f"{person.id}/servings/{participant['serving_id']}/consumption"
    )


def _participant_consumption_path(family, person, event) -> str:
    return (
        f"/api/families/{family.id}/meal-plan/{event.id}/participants/"
        f"{person.id}/consumption"
    )


def test_consumed_meal_moves_energy_from_planned_to_consumed(db_session: Session) -> None:
    family, person, entry, participant = _setup(db_session, "lunch", "13:00")

    response = _request(
        db_session,
        "PATCH",
        _consumption_path(family, person, entry, participant),
        json={"status": "consumed"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "consumed"
    assert Decimal(body["quantity_consumed"]) == Decimal(400)
    assert Decimal(body["energy_consumed_kcal"]) == Decimal(400)
    state = body["daily_nutrition_state"]
    assert Decimal(state["energy_consumed_kcal"]) == Decimal(400)
    assert Decimal(state["energy_planned_kcal"]) == Decimal(0)
    assert Decimal(state["energy_assumed_kcal"]) == Decimal(350)
    assert Decimal(state["energy_remaining_min_kcal"]) == Decimal(1050)
    assert Decimal(state["energy_remaining_max_kcal"]) == Decimal(1250)


def test_partial_consumption_scales_catalogue_nutrition(db_session: Session) -> None:
    family, person, entry, participant = _setup(db_session, "lunch", "13:00")

    response = _request(
        db_session,
        "PATCH",
        _consumption_path(family, person, entry, participant),
        json={"status": "partial", "quantity_consumed": "200"},
    )

    assert response.status_code == 200
    body = response.json()
    assert Decimal(body["quantity_consumed"]) == Decimal(200)
    assert Decimal(body["energy_consumed_kcal"]) == Decimal(200)
    state = body["daily_nutrition_state"]
    assert Decimal(state["energy_consumed_kcal"]) == Decimal(200)
    assert Decimal(state["energy_planned_kcal"]) == Decimal(0)
    assert Decimal(state["energy_assumed_kcal"]) == Decimal(350)


def test_consumed_legacy_serving_uses_persisted_planned_nutrition(
    db_session: Session,
) -> None:
    family, person, entry, participant = _setup(db_session, "lunch", "13:00")
    serving = db_session.get(Serving, uuid.UUID(participant["serving_id"]))
    assert serving is not None
    assert serving.energy_planned_kcal == Decimal("400.00")

    # Simulate a legacy serving whose unit no longer converts directly to the bound catalogue
    # composition. Consumption should scale the authoritative persisted plan instead of 500ing.
    serving.quantity_unit = "serving"
    db_session.flush()

    response = _request(
        db_session,
        "PATCH",
        _consumption_path(family, person, entry, participant),
        json={"status": "consumed"},
    )

    assert response.status_code == 200
    assert Decimal(response.json()["energy_consumed_kcal"]) == Decimal("400.00")


def test_skipped_breakfast_is_declared_zero_and_removes_later_assumption(
    db_session: Session,
) -> None:
    family, person, entry, participant = _setup(db_session, "breakfast", "08:30")

    skipped = _request(
        db_session,
        "PATCH",
        _consumption_path(family, person, entry, participant),
        json={"status": "skipped"},
    )
    assert skipped.status_code == 200
    assert Decimal(skipped.json()["daily_nutrition_state"]["energy_assumed_kcal"]) == Decimal(0)
    event = db_session.get(MealEvent, uuid.UUID(entry["id"]))
    assert event is not None
    assert event.status == "completed"
    assert event.served_at is None

    lunch = get_planning_bootstrap(
        db_session,
        person_id=person.id,
        scheduled_at=datetime(2026, 8, 23, 13, 0, tzinfo=ZoneInfo("Europe/Lisbon")),
        ensure_state=True,
    )
    assert lunch.daily_nutrition_state is not None
    assert lunch.daily_nutrition_state.energy_assumed_kcal == Decimal(0)
    assert lunch.daily_nutrition_state.energy_remaining_min_kcal == Decimal("1800.00")
    assert lunch.daily_nutrition_state.energy_remaining_max_kcal == Decimal("2000.00")


def test_legacy_breakfast_without_serving_can_be_marked_consumed(
    db_session: Session,
) -> None:
    family, person, event, participant = _setup_legacy_without_serving(db_session, "breakfast")

    response = _request(
        db_session,
        "PATCH",
        _participant_consumption_path(family, person, event),
        json={"status": "consumed"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "consumed"
    assert Decimal(body["quantity_planned"]) == Decimal(1)
    assert Decimal(body["quantity_consumed"]) == Decimal(1)
    assert body["quantity_unit"] == "serving"
    assert Decimal(body["energy_planned_kcal"]) == Decimal(350)
    assert Decimal(body["energy_consumed_kcal"]) == Decimal(350)
    state = body["daily_nutrition_state"]
    assert Decimal(state["energy_consumed_kcal"]) == Decimal(350)
    assert Decimal(state["energy_planned_kcal"]) == Decimal(0)
    assert Decimal(state["energy_assumed_kcal"]) == Decimal(0)

    db_session.expire_all()
    serving = db_session.get(Serving, uuid.UUID(body["serving_id"]))
    assert serving is not None
    assert serving.meal_participant_id == participant.id
    assert serving.nutrition_source == "estimated"
    assert serving.nutrition_calculation_version == "standard-breakfast-fallback-v1"
    assert serving.source_reference == "nutriflow:standard-breakfast-fallback"


def test_non_breakfast_without_serving_requires_explicit_serving(
    db_session: Session,
) -> None:
    family, person, event, _ = _setup_legacy_without_serving(db_session, "lunch")

    response = _request(
        db_session,
        "PATCH",
        _participant_consumption_path(family, person, event),
        json={"status": "consumed"},
    )

    assert response.status_code == 422
    assert "Only legacy breakfast events" in response.json()["detail"]
