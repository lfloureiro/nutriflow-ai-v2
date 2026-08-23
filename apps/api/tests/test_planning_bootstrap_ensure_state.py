from datetime import UTC, date, datetime
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.main import app
from app.models.daily_nutrition_state import DailyNutritionState
from app.models.family import Family
from app.models.meal import MealEvent, MealParticipant, Serving
from app.models.nutrition_target import NutritionTarget
from app.models.person import Person


def _override_db(db_session: Session):
    def override_get_db():
        yield db_session

    return override_get_db


def test_recommendation_bootstrap_can_materialize_missing_daily_state(
    db_session: Session,
) -> None:
    family = Family(name="Future planning family", timezone="Europe/Lisbon")
    person = Person(
        family=family,
        first_name="Ana",
        preferred_locale="pt-PT",
        timezone="Europe/Lisbon",
    )
    db_session.add(family)
    db_session.flush()

    app.dependency_overrides[get_db] = _override_db(db_session)
    try:
        with TestClient(app) as client:
            response = client.get(
                f"/api/persons/{person.id}/planning-bootstrap",
                params={
                    "scheduled_at": datetime(2026, 8, 25, 12, 0, tzinfo=UTC).isoformat(),
                    "ensure_state": "true",
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    state = response.json()["daily_nutrition_state"]
    assert state is not None
    assert state["state_date"] == "2026-08-25"
    assert state["calculation_version"] == "daily-nutrition-from-servings-v1"
    assert db_session.scalar(select(DailyNutritionState)) is not None


def test_recommendation_bootstrap_refreshes_existing_serving_derived_state(
    db_session: Session,
) -> None:
    planning_date = date(2026, 8, 25)
    scheduled_at = datetime(2026, 8, 25, 12, 0, tzinfo=UTC)
    family = Family(name="Refresh planning family", timezone="Europe/Lisbon")
    person = Person(
        family=family,
        first_name="Bruno",
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
        meal_type="lunch",
        title="Lunch",
        scheduled_at=scheduled_at,
        timezone="Europe/Lisbon",
        status="planned",
        source="test",
    )
    participant = MealParticipant(
        meal_event=event,
        person=person,
        status="planned",
    )
    serving = Serving(
        meal_participant=participant,
        item_type="dish",
        item_key="test:lunch",
        item_name="Test lunch",
        status="planned",
        quantity_planned=Decimal(1),
        quantity_unit="serving",
        energy_planned_kcal=Decimal(600),
        nutrition_source="test",
    )
    stale_state = DailyNutritionState(
        person=person,
        nutrition_target=target,
        state_date=planning_date,
        timezone="Europe/Lisbon",
        energy_consumed_kcal=Decimal(0),
        energy_planned_kcal=Decimal(0),
        energy_remaining_min_kcal=Decimal(1800),
        energy_remaining_max_kcal=Decimal(2000),
        calculation_version="daily-nutrition-from-servings-v1",
    )
    db_session.add_all([family, serving, stale_state])
    db_session.flush()

    app.dependency_overrides[get_db] = _override_db(db_session)
    try:
        with TestClient(app) as client:
            response = client.get(
                f"/api/persons/{person.id}/planning-bootstrap",
                params={
                    "scheduled_at": scheduled_at.isoformat(),
                    "ensure_state": "true",
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    state = response.json()["daily_nutrition_state"]
    assert state["energy_planned_kcal"] == "600.00"
    assert state["energy_remaining_min_kcal"] == "1200.00"
    assert state["energy_remaining_max_kcal"] == "1400.00"
