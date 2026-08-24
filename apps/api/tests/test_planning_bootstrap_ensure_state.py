from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

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
from app.models.person_profile import PersonProfile

LISBON = ZoneInfo("Europe/Lisbon")


def _override_db(db_session: Session):
    def override_get_db():
        yield db_session

    return override_get_db


def _lisbon_date(offset_days: int) -> date:
    return datetime.now(UTC).astimezone(LISBON).date() + timedelta(days=offset_days)


def _local_datetime(on_date: date, at_time: time) -> datetime:
    return datetime.combine(on_date, at_time, tzinfo=LISBON)


def test_recommendation_bootstrap_can_materialize_future_daily_state_without_breakfast_assumption(
    db_session: Session,
) -> None:
    planning_date = _lisbon_date(2)
    scheduled_at = _local_datetime(planning_date, time(12, 0))
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
                    "scheduled_at": scheduled_at.isoformat(),
                    "ensure_state": "true",
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    state = response.json()["daily_nutrition_state"]
    assert state is not None
    assert state["state_date"] == planning_date.isoformat()
    assert state["calculation_version"] == "daily-nutrition-from-servings-v1"
    assert state["energy_assumed_kcal"] == "0.00"
    assert db_session.scalar(select(DailyNutritionState)) is not None


def test_recommendation_bootstrap_refreshes_existing_future_serving_derived_state(
    db_session: Session,
) -> None:
    planning_date = _lisbon_date(2)
    scheduled_at = _local_datetime(planning_date, time(12, 0))
    family = Family(name="Refresh planning family", timezone="Europe/Lisbon")
    person = Person(
        family=family,
        first_name="Bruno",
        preferred_locale="pt-PT",
        timezone="Europe/Lisbon",
    )
    target = NutritionTarget(
        person=person,
        valid_from=date(2020, 1, 1),
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
        energy_assumed_kcal=Decimal(0),
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
    assert state["energy_assumed_kcal"] == "0.00"
    assert state["energy_remaining_min_kcal"] == "1200.00"
    assert state["energy_remaining_max_kcal"] == "1400.00"


def test_missing_past_breakfast_is_assumed_then_replaced_by_declared_breakfast(
    db_session: Session,
) -> None:
    planning_date = _lisbon_date(-1)
    lunch_time = _local_datetime(planning_date, time(12, 0))
    breakfast_time = _local_datetime(planning_date, time(8, 30))
    family = Family(name="Breakfast assumption family", timezone="Europe/Lisbon")
    person = Person(
        family=family,
        first_name="Carla",
        preferred_locale="pt-PT",
        timezone="Europe/Lisbon",
    )
    person.profile = PersonProfile(
        person=person,
        sex_for_energy_calculation="female",
        activity_level="light",
        standard_breakfast_kcal=Decimal(320),
    )
    target = NutritionTarget(
        person=person,
        valid_from=date(2020, 1, 1),
        energy_min_kcal=Decimal(1800),
        energy_max_kcal=Decimal(2000),
        calculation_version="test-target-v1",
        status="active",
        source="test",
    )
    db_session.add_all([family, target])
    db_session.flush()

    app.dependency_overrides[get_db] = _override_db(db_session)
    try:
        with TestClient(app) as client:
            assumed_response = client.get(
                f"/api/persons/{person.id}/planning-bootstrap",
                params={"scheduled_at": lunch_time.isoformat(), "ensure_state": "true"},
            )
            assert assumed_response.status_code == 200
            assumed = assumed_response.json()["daily_nutrition_state"]
            assert assumed["energy_assumed_kcal"] == "320.00"
            assert assumed["energy_remaining_min_kcal"] == "1480.00"
            assert assumed["energy_remaining_max_kcal"] == "1680.00"

            breakfast_event = MealEvent(
                family=family,
                meal_type="breakfast",
                title="Breakfast",
                scheduled_at=breakfast_time,
                timezone="Europe/Lisbon",
                status="planned",
                source="test",
            )
            breakfast_participant = MealParticipant(
                meal_event=breakfast_event,
                person=person,
                status="planned",
            )
            breakfast_serving = Serving(
                meal_participant=breakfast_participant,
                item_type="dish",
                item_key="test:breakfast",
                item_name="Declared breakfast",
                status="planned",
                quantity_planned=Decimal(1),
                quantity_unit="serving",
                energy_planned_kcal=Decimal(400),
                nutrition_source="test",
            )
            db_session.add(breakfast_serving)
            db_session.flush()

            declared_response = client.get(
                f"/api/persons/{person.id}/planning-bootstrap",
                params={"scheduled_at": lunch_time.isoformat(), "ensure_state": "true"},
            )
    finally:
        app.dependency_overrides.clear()

    assert declared_response.status_code == 200
    declared = declared_response.json()["daily_nutrition_state"]
    assert declared["state_date"] == planning_date.isoformat()
    assert declared["energy_planned_kcal"] == "400.00"
    assert declared["energy_assumed_kcal"] == "0.00"
    assert declared["energy_remaining_min_kcal"] == "1400.00"
    assert declared["energy_remaining_max_kcal"] == "1600.00"
