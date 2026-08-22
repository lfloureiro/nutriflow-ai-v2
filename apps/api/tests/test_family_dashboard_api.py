import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.main import app
from app.models.daily_health_state import DailyHealthState
from app.models.daily_nutrition_state import DailyNutritionState
from app.models.family import Family
from app.models.meal import MealEvent, MealParticipant
from app.models.person import Person

DASHBOARD_DATE = date(2026, 8, 22)


def _override_db(db_session: Session):
    def override_get_db():
        yield db_session

    return override_get_db


def _get(db_session: Session, family_id: uuid.UUID | str, on_date: date = DASHBOARD_DATE):
    app.dependency_overrides[get_db] = _override_db(db_session)
    try:
        with TestClient(app) as client:
            return client.get(
                f"/api/families/{family_id}/dashboard",
                params={"on_date": on_date.isoformat()},
            )
    finally:
        app.dependency_overrides.clear()


def test_family_dashboard_returns_latest_member_states_and_local_day_meals(
    db_session: Session,
) -> None:
    family = Family(name="Dashboard family", timezone="Europe/Lisbon")
    ana = Person(family=family, first_name="Ana", timezone="Europe/Lisbon")
    rui = Person(family=family, first_name="Rui", timezone="Europe/Lisbon")
    db_session.add(family)
    db_session.flush()

    db_session.add_all(
        [
            DailyHealthState(
                person=ana,
                state_date=DASHBOARD_DATE,
                timezone="Europe/Lisbon",
                steps=3000,
                calculation_version="older",
                computed_at=datetime(2026, 8, 22, 8, 0, tzinfo=UTC),
            ),
            DailyHealthState(
                person=ana,
                state_date=DASHBOARD_DATE,
                timezone="Europe/Lisbon",
                latest_weight_kg=Decimal("70.500"),
                weight_trend_7d_kg=Decimal("-0.400"),
                steps=8000,
                sleep_duration_minutes=430,
                calculation_version="latest",
                computed_at=datetime(2026, 8, 22, 9, 0, tzinfo=UTC),
            ),
            DailyNutritionState(
                person=ana,
                state_date=DASHBOARD_DATE,
                timezone="Europe/Lisbon",
                energy_consumed_kcal=Decimal("950.00"),
                energy_planned_kcal=Decimal("600.00"),
                energy_remaining_min_kcal=Decimal("250.00"),
                energy_remaining_max_kcal=Decimal("550.00"),
                adherence_score=Decimal("0.8200"),
                calculation_version="latest",
                computed_at=datetime(2026, 8, 22, 9, 5, tzinfo=UTC),
            ),
        ]
    )

    early_local_meal = MealEvent(
        family=family,
        meal_type="breakfast",
        title="Breakfast",
        scheduled_at=datetime(2026, 8, 21, 23, 30, tzinfo=UTC),
        timezone="Europe/Lisbon",
        status="completed",
    )
    dinner = MealEvent(
        family=family,
        meal_type="dinner",
        title="Family dinner",
        scheduled_at=datetime(2026, 8, 22, 19, 0, tzinfo=UTC),
        timezone="Europe/Lisbon",
        status="planned",
    )
    next_local_day = MealEvent(
        family=family,
        meal_type="snack",
        title="Too late",
        scheduled_at=datetime(2026, 8, 22, 23, 30, tzinfo=UTC),
        timezone="Europe/Lisbon",
        status="planned",
    )
    cancelled = MealEvent(
        family=family,
        meal_type="lunch",
        title="Cancelled",
        scheduled_at=datetime(2026, 8, 22, 12, 0, tzinfo=UTC),
        timezone="Europe/Lisbon",
        status="cancelled",
    )
    db_session.add_all(
        [
            early_local_meal,
            dinner,
            next_local_day,
            cancelled,
            MealParticipant(meal_event=early_local_meal, person=ana),
            MealParticipant(meal_event=dinner, person=ana),
            MealParticipant(meal_event=dinner, person=rui),
        ]
    )
    db_session.flush()

    response = _get(db_session, family.id)

    assert response.status_code == 200
    body = response.json()
    assert body["family_name"] == "Dashboard family"
    assert body["dashboard_date"] == "2026-08-22"
    assert [member["first_name"] for member in body["members"]] == ["Ana", "Rui"]

    ana_body = body["members"][0]
    assert ana_body["health"]["steps"] == 8000
    assert Decimal(ana_body["health"]["latest_weight_kg"]) == Decimal("70.500")
    assert Decimal(ana_body["nutrition"]["energy_consumed_kcal"]) == Decimal("950.00")
    assert body["members"][1]["health"] is None
    assert body["members"][1]["nutrition"] is None

    assert [meal["title"] for meal in body["meals"]] == ["Breakfast", "Family dinner"]
    assert set(body["meals"][1]["participant_person_ids"]) == {str(ana.id), str(rui.id)}


def test_family_dashboard_keeps_missing_evidence_explicit(db_session: Session) -> None:
    family = Family(name="Empty dashboard", timezone="Europe/Lisbon")
    person = Person(family=family, first_name="No data", timezone="Europe/Lisbon")
    db_session.add(family)
    db_session.flush()

    response = _get(db_session, family.id)

    assert response.status_code == 200
    body = response.json()
    assert len(body["members"]) == 1
    assert body["members"][0]["person_id"] == str(person.id)
    assert body["members"][0]["health"] is None
    assert body["members"][0]["nutrition"] is None
    assert body["meals"] == []


def test_family_dashboard_returns_404_for_unknown_family(db_session: Session) -> None:
    response = _get(db_session, "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")

    assert response.status_code == 404
    assert response.json()["detail"] == "Family not found"
