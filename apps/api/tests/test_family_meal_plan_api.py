import uuid
from datetime import UTC, datetime
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.main import app
from app.models.family import Family
from app.models.food_catalog import FoodCompositionSnapshot, FoodItem
from app.models.person import Person

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


def _recipe(db_session: Session, family: Family) -> str:
    ingredient = FoodItem(
        family=family,
        catalog_key=f"test:planner:{uuid.uuid4()}",
        name="Base da receita",
        food_kind="ingredient",
        source="test",
        is_active=True,
    )
    ingredient.compositions.append(
        FoodCompositionSnapshot(
            reference_quantity=Decimal("100"),
            reference_unit="g",
            energy_kcal=Decimal("100"),
            data_version="test-v1",
            source="test",
            effective_at=datetime.now(UTC),
        )
    )
    db_session.add(ingredient)
    db_session.flush()
    response = _request(
        db_session,
        "POST",
        f"/api/families/{family.id}/recipes",
        json={
            "name": "Receita de planeamento",
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


def test_family_meal_plan_exposes_four_slots_and_supports_create_update_cancel(
    db_session: Session,
) -> None:
    family = Family(name="Planner family", timezone="Europe/Lisbon")
    ana = Person(family=family, first_name="Ana", timezone="Europe/Lisbon")
    rui = Person(family=family, first_name="Rui", timezone="Europe/Lisbon")
    db_session.add(family)
    db_session.flush()
    recipe_id = _recipe(db_session, family)

    created = _request(
        db_session,
        "POST",
        f"/api/families/{family.id}/meal-plan",
        json={
            "date": PLAN_DATE,
            "meal_type": "dinner",
            "local_time": "20:00",
            "recipe_id": recipe_id,
            "location": "Casa",
            "participants": [
                {"person_id": str(ana.id), "quantity": "300", "unit": "g"},
                {"person_id": str(rui.id), "quantity": "500", "unit": "g"},
            ],
        },
    )
    assert created.status_code == 201
    entry = created.json()
    assert entry["meal_type"] == "dinner"
    assert entry["recipe_name"] == "Receita de planeamento"
    assert [Decimal(item["energy_kcal"]) for item in entry["participants"]] == [
        Decimal("300"),
        Decimal("500"),
    ]

    plan = _request(
        db_session,
        "GET",
        f"/api/families/{family.id}/meal-plan",
        params={"start_date": PLAN_DATE, "days": 1},
    )
    assert plan.status_code == 200
    slots = plan.json()["days"][0]["slots"]
    assert [slot["meal_type"] for slot in slots] == ["breakfast", "lunch", "snack", "dinner"]
    assert [len(slot["meals"]) for slot in slots] == [0, 0, 0, 1]

    updated = _request(
        db_session,
        "PATCH",
        f"/api/families/{family.id}/meal-plan/{entry['id']}",
        json={
            "local_time": "19:30",
            "participants": [
                {"person_id": str(ana.id), "quantity": "400", "unit": "g"},
                {"person_id": str(rui.id), "quantity": "500", "unit": "g"},
            ],
        },
    )
    assert updated.status_code == 200
    assert updated.json()["local_time"].startswith("19:30")
    assert Decimal(updated.json()["participants"][0]["energy_kcal"]) == Decimal("400")

    removed = _request(
        db_session,
        "DELETE",
        f"/api/families/{family.id}/meal-plan/{entry['id']}",
    )
    assert removed.status_code == 204
    plan_after = _request(
        db_session,
        "GET",
        f"/api/families/{family.id}/meal-plan",
        params={"start_date": PLAN_DATE, "days": 1},
    )
    assert all(slot["meals"] == [] for slot in plan_after.json()["days"][0]["slots"])


def test_family_meal_plan_rejects_unknown_meal_types_and_cross_family_people(
    db_session: Session,
) -> None:
    family = Family(name="Planner A", timezone="Europe/Lisbon")
    other_family = Family(name="Planner B", timezone="Europe/Lisbon")
    own_person = Person(family=family, first_name="Ana", timezone="Europe/Lisbon")
    other_person = Person(family=other_family, first_name="Outro", timezone="Europe/Lisbon")
    db_session.add_all([family, other_family])
    db_session.flush()
    recipe_id = _recipe(db_session, family)

    invalid_type = _request(
        db_session,
        "POST",
        f"/api/families/{family.id}/meal-plan",
        json={
            "date": PLAN_DATE,
            "meal_type": "brunch",
            "local_time": "11:00",
            "recipe_id": recipe_id,
            "participants": [{"person_id": str(own_person.id)}],
        },
    )
    assert invalid_type.status_code == 422

    cross_family = _request(
        db_session,
        "POST",
        f"/api/families/{family.id}/meal-plan",
        json={
            "date": PLAN_DATE,
            "meal_type": "lunch",
            "local_time": "13:00",
            "recipe_id": recipe_id,
            "participants": [{"person_id": str(other_person.id)}],
        },
    )
    assert cross_family.status_code == 422
