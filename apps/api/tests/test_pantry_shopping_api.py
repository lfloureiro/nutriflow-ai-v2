from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.main import app
from app.models.family import Family
from app.models.person import Person

PLAN_DATE = "2026-08-24"


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


def _ingredient(db_session: Session, family: Family, name: str) -> dict:
    response = _request(
        db_session,
        "POST",
        f"/api/families/{family.id}/ingredients",
        json={
            "name": name,
            "composition": {
                "reference_quantity": "100",
                "reference_unit": "g",
                "energy_kcal": "100",
            },
        },
    )
    assert response.status_code == 201
    return response.json()


def _recipe(db_session: Session, family: Family, ingredient_id: str) -> dict:
    response = _request(
        db_session,
        "POST",
        f"/api/families/{family.id}/recipes",
        json={
            "name": "Receita para compras",
            "serving_count": "2",
            "yield_quantity": "400",
            "yield_unit": "g",
            "ingredients": [
                {"food_item_id": ingredient_id, "quantity": "200", "unit": "g"}
            ],
        },
    )
    assert response.status_code == 201
    return response.json()


def test_pantry_lot_crud_and_soft_deactivation(db_session: Session) -> None:
    family = Family(name="Pantry family", timezone="Europe/Lisbon")
    db_session.add(family)
    db_session.flush()
    ingredient = _ingredient(db_session, family, "Arroz")

    created = _request(
        db_session,
        "POST",
        f"/api/families/{family.id}/pantry",
        json={
            "food_item_id": ingredient["id"],
            "quantity_available": "250",
            "unit": "g",
            "location": "Despensa",
        },
    )
    assert created.status_code == 201
    lot = created.json()
    assert lot["food_item_name"] == "Arroz"
    assert Decimal(lot["quantity_available"]) == Decimal(250)

    updated = _request(
        db_session,
        "PATCH",
        f"/api/families/{family.id}/pantry/{lot['id']}",
        json={"quantity_available": "300", "unit": "g"},
    )
    assert updated.status_code == 200
    assert Decimal(updated.json()["quantity_available"]) == Decimal(300)

    removed = _request(
        db_session,
        "DELETE",
        f"/api/families/{family.id}/pantry/{lot['id']}",
    )
    assert removed.status_code == 204
    active = _request(db_session, "GET", f"/api/families/{family.id}/pantry")
    assert active.json() == []
    inactive = _request(
        db_session,
        "GET",
        f"/api/families/{family.id}/pantry",
        params={"include_inactive": True},
    )
    assert len(inactive.json()) == 1
    assert inactive.json()[0]["is_available"] is False


def test_shopping_refresh_aggregates_plan_before_subtracting_pantry(db_session: Session) -> None:
    family = Family(name="Shopping family", timezone="Europe/Lisbon")
    ana = Person(family=family, first_name="Ana", timezone="Europe/Lisbon")
    rui = Person(family=family, first_name="Rui", timezone="Europe/Lisbon")
    db_session.add(family)
    db_session.flush()
    ingredient = _ingredient(db_session, family, "Massa")
    recipe = _recipe(db_session, family, ingredient["id"])

    pantry = _request(
        db_session,
        "POST",
        f"/api/families/{family.id}/pantry",
        json={
            "food_item_id": ingredient["id"],
            "quantity_available": "250",
            "unit": "g",
        },
    )
    assert pantry.status_code == 201

    for meal_type, local_time in (("lunch", "13:00"), ("dinner", "20:00")):
        planned = _request(
            db_session,
            "POST",
            f"/api/families/{family.id}/meal-plan",
            json={
                "date": PLAN_DATE,
                "meal_type": meal_type,
                "local_time": local_time,
                "recipe_id": recipe["id"],
                "participants": [
                    {"person_id": str(ana.id), "quantity": "100", "unit": "g"},
                    {"person_id": str(rui.id), "quantity": "300", "unit": "g"},
                ],
            },
        )
        assert planned.status_code == 201

    refreshed = _request(
        db_session,
        "POST",
        f"/api/families/{family.id}/shopping-list/refresh",
        json={"start_date": PLAN_DATE, "days": 1},
    )
    assert refreshed.status_code == 200
    body = refreshed.json()
    requirement = body["requirements"][0]
    assert Decimal(requirement["required_quantity"]) == Decimal(400)
    assert Decimal(requirement["available_quantity"]) == Decimal(250)
    assert Decimal(requirement["missing_quantity"]) == Decimal(150)
    assert body["planning_issues"] == []
    assert len(body["items"]) == 1
    assert body["items"][0]["item_source"] == "automatic"
    assert Decimal(body["items"][0]["quantity"]) == Decimal(150)


def test_manual_shopping_item_can_be_checked_and_removed(db_session: Session) -> None:
    family = Family(name="Manual shopping family", timezone="Europe/Lisbon")
    db_session.add(family)
    db_session.flush()

    added = _request(
        db_session,
        "POST",
        f"/api/families/{family.id}/shopping-list/items",
        json={"name": "Detergente"},
    )
    assert added.status_code == 201
    item = added.json()["items"][0]
    assert item["item_source"] == "manual"
    assert item["status"] == "needed"

    checked = _request(
        db_session,
        "PATCH",
        f"/api/families/{family.id}/shopping-list/items/{item['id']}",
        json={"status": "purchased"},
    )
    assert checked.status_code == 200
    assert checked.json()["items"][0]["status"] == "purchased"

    removed = _request(
        db_session,
        "DELETE",
        f"/api/families/{family.id}/shopping-list/items/{item['id']}",
    )
    assert removed.status_code == 204
    final = _request(db_session, "GET", f"/api/families/{family.id}/shopping-list")
    assert final.status_code == 200
    assert final.json()["items"] == []


def test_pantry_rejects_food_from_another_family(db_session: Session) -> None:
    family = Family(name="Pantry A", timezone="Europe/Lisbon")
    other = Family(name="Pantry B", timezone="Europe/Lisbon")
    db_session.add_all([family, other])
    db_session.flush()
    foreign_ingredient = _ingredient(db_session, other, "Ingrediente privado")

    response = _request(
        db_session,
        "POST",
        f"/api/families/{family.id}/pantry",
        json={
            "food_item_id": foreign_ingredient["id"],
            "quantity_available": "1",
            "unit": "kg",
        },
    )
    assert response.status_code == 422
