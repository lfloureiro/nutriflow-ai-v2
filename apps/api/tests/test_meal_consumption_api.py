from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.main import app
from app.models.family import Family
from app.models.nutrition_target import NutritionTarget
from app.models.person import Person
from app.services.planning_bootstrap_api import get_planning_bootstrap
from tests.test_family_meal_plan_api import PLAN_DATE, _recipe


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
    db_session.add(family)
    db_session.flush()
    recipe_id = _recipe(db_session, family)
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


def _consumption_path(family, person, entry, participant) -> str:
    return (
        f"/api/families/{family.id}/meal-plan/{entry['id']}/participants/"
        f"{person.id}/servings/{participant['serving_id']}/consumption"
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

    lunch = get_planning_bootstrap(
        db_session,
        person_id=person.id,
        scheduled_at=entry_datetime := __import__("datetime").datetime.fromisoformat(
            f"{PLAN_DATE}T13:00:00+01:00"
        ),
        ensure_state=True,
    )
    assert entry_datetime.hour == 13
    assert lunch.daily_nutrition_state is not None
    assert lunch.daily_nutrition_state.energy_assumed_kcal == Decimal(0)
    assert lunch.daily_nutrition_state.energy_remaining_min_kcal == Decimal("1800.00")
    assert lunch.daily_nutrition_state.energy_remaining_max_kcal == Decimal("2000.00")
