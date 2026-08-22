import uuid
from datetime import date, datetime
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.main import app
from app.models.family import Family
from app.models.meal import MealEvent, MealParticipant, Serving
from app.models.person import Person

START_DATE = date(2026, 8, 22)


def _override_db(db_session: Session):
    def override_get_db():
        yield db_session

    return override_get_db


def _get(
    db_session: Session,
    family_id: uuid.UUID | str,
    *,
    start_date: date = START_DATE,
    days: int = 7,
):
    app.dependency_overrides[get_db] = _override_db(db_session)
    try:
        with TestClient(app) as client:
            return client.get(
                f"/api/families/{family_id}/meals",
                params={"start_date": start_date.isoformat(), "days": days},
            )
    finally:
        app.dependency_overrides.clear()


def _get_detail(
    db_session: Session,
    family_id: uuid.UUID | str,
    meal_event_id: uuid.UUID | str,
):
    app.dependency_overrides[get_db] = _override_db(db_session)
    try:
        with TestClient(app) as client:
            return client.get(f"/api/families/{family_id}/meals/{meal_event_id}")
    finally:
        app.dependency_overrides.clear()


def test_family_meals_returns_local_calendar_days_and_participant_names(
    db_session: Session,
) -> None:
    family = Family(name="Meal map family", timezone="Europe/Lisbon")
    ana = Person(family=family, first_name="Ana", last_name="Silva", timezone="Europe/Lisbon")
    rui = Person(family=family, first_name="Rui", timezone="Europe/Lisbon")
    db_session.add(family)
    db_session.flush()

    breakfast = MealEvent(
        family=family,
        meal_type="breakfast",
        title="Pequeno-almoço",
        scheduled_at=datetime.fromisoformat("2026-08-21T23:30:00+00:00"),
        timezone="Europe/Lisbon",
        status="completed",
        location="Casa",
    )
    dinner = MealEvent(
        family=family,
        meal_type="dinner",
        title="Jantar em família",
        scheduled_at=datetime.fromisoformat("2026-08-24T19:00:00+00:00"),
        timezone="Europe/Lisbon",
        status="planned",
    )
    cancelled = MealEvent(
        family=family,
        meal_type="lunch",
        title="Cancelado",
        scheduled_at=datetime.fromisoformat("2026-08-23T12:00:00+00:00"),
        timezone="Europe/Lisbon",
        status="cancelled",
    )
    outside_range = MealEvent(
        family=family,
        meal_type="snack",
        title="Fora da semana",
        scheduled_at=datetime.fromisoformat("2026-08-28T23:30:00+00:00"),
        timezone="Europe/Lisbon",
        status="planned",
    )
    db_session.add_all(
        [
            breakfast,
            dinner,
            cancelled,
            outside_range,
            MealParticipant(meal_event=breakfast, person=ana, status="consumed"),
            MealParticipant(meal_event=dinner, person=ana, status="planned"),
            MealParticipant(meal_event=dinner, person=rui, status="planned"),
        ]
    )
    db_session.flush()

    response = _get(db_session, family.id)

    assert response.status_code == 200
    body = response.json()
    assert body["family_name"] == "Meal map family"
    assert body["timezone"] == "Europe/Lisbon"
    assert body["start_date"] == "2026-08-22"
    assert body["end_date"] == "2026-08-28"
    assert [day["date"] for day in body["days"]] == [
        "2026-08-22",
        "2026-08-23",
        "2026-08-24",
        "2026-08-25",
        "2026-08-26",
        "2026-08-27",
        "2026-08-28",
    ]
    assert [meal["title"] for meal in body["days"][0]["meals"]] == ["Pequeno-almoço"]
    assert body["days"][1]["meals"] == []
    assert [meal["title"] for meal in body["days"][2]["meals"]] == ["Jantar em família"]
    assert body["days"][2]["meals"][0]["participants"] == [
        {
            "person_id": str(ana.id),
            "first_name": "Ana",
            "last_name": "Silva",
            "status": "planned",
        },
        {
            "person_id": str(rui.id),
            "first_name": "Rui",
            "last_name": None,
            "status": "planned",
        },
    ]
    assert all(
        meal["title"] not in {"Cancelado", "Fora da semana"}
        for day in body["days"]
        for meal in day["meals"]
    )


def test_family_meals_validates_range_size(db_session: Session) -> None:
    family = Family(name="Range family", timezone="Europe/Lisbon")
    db_session.add(family)
    db_session.flush()

    assert _get(db_session, family.id, days=0).status_code == 422
    assert _get(db_session, family.id, days=15).status_code == 422


def test_family_meals_returns_404_for_unknown_family(db_session: Session) -> None:
    response = _get(db_session, "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")

    assert response.status_code == 404
    assert response.json()["detail"] == "Family not found"


def test_family_meal_detail_returns_person_specific_servings(db_session: Session) -> None:
    family = Family(name="Detail family", timezone="Europe/Lisbon")
    ana = Person(family=family, first_name="Ana", last_name="Silva", timezone="Europe/Lisbon")
    rui = Person(family=family, first_name="Rui", timezone="Europe/Lisbon")
    meal = MealEvent(
        family=family,
        meal_type="dinner",
        title="Jantar em família",
        scheduled_at=datetime.fromisoformat("2026-08-22T19:00:00+00:00"),
        timezone="Europe/Lisbon",
        status="planned",
        location="Casa",
    )
    ana_participant = MealParticipant(meal_event=meal, person=ana, status="planned")
    rui_participant = MealParticipant(meal_event=meal, person=rui, status="planned")
    ana_serving = Serving(
        meal_participant=ana_participant,
        item_type="dish",
        item_name="Salmão com batata e salada",
        status="planned",
        quantity_planned=Decimal("320.0000"),
        quantity_unit="g",
        energy_planned_kcal=Decimal("448.00"),
    )
    rui_serving = Serving(
        meal_participant=rui_participant,
        item_type="dish",
        item_name="Salmão com batata e salada",
        status="planned",
        quantity_planned=Decimal("500.0000"),
        quantity_unit="g",
        energy_planned_kcal=Decimal("700.00"),
    )
    db_session.add_all([meal, ana_serving, rui_serving])
    db_session.flush()

    response = _get_detail(db_session, family.id, meal.id)

    assert response.status_code == 200
    body = response.json()
    assert body["family_id"] == str(family.id)
    assert body["family_name"] == "Detail family"
    assert body["timezone"] == "Europe/Lisbon"
    assert body["id"] == str(meal.id)
    assert body["title"] == "Jantar em família"
    assert body["location"] == "Casa"
    assert [participant["first_name"] for participant in body["participants"]] == ["Ana", "Rui"]
    assert body["participants"][0]["servings"] == [
        {
            "id": str(ana_serving.id),
            "item_type": "dish",
            "item_name": "Salmão com batata e salada",
            "status": "planned",
            "quantity_planned": "320.0000",
            "quantity_served": None,
            "quantity_consumed": None,
            "quantity_unit": "g",
            "energy_planned_kcal": "448.00",
            "energy_served_kcal": None,
            "energy_consumed_kcal": None,
        }
    ]
    assert body["participants"][1]["servings"][0]["quantity_planned"] == "500.0000"
    assert body["participants"][1]["servings"][0]["energy_planned_kcal"] == "700.00"


def test_family_meal_detail_is_scoped_to_family(db_session: Session) -> None:
    family = Family(name="Requested family", timezone="Europe/Lisbon")
    other_family = Family(name="Other family", timezone="Europe/Lisbon")
    other_meal = MealEvent(
        family=other_family,
        meal_type="lunch",
        scheduled_at=datetime.fromisoformat("2026-08-22T12:00:00+00:00"),
        timezone="Europe/Lisbon",
        status="planned",
    )
    db_session.add_all([family, other_family, other_meal])
    db_session.flush()

    response = _get_detail(db_session, family.id, other_meal.id)

    assert response.status_code == 404
    assert response.json()["detail"] == "Meal not found"
