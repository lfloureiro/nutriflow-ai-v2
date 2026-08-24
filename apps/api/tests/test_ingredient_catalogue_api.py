import uuid

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.main import app
from app.models.family import Family
from app.models.food_catalog import FoodCompositionSnapshot, FoodItem


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


def _composition(energy_kcal: str = "370") -> dict[str, object]:
    return {
        "reference_quantity": "100",
        "reference_unit": "g",
        "energy_kcal": energy_kcal,
        "nutrients": [
            {"key": "protein", "value": "13.5", "unit": "g"},
            {"key": "carbohydrate", "value": "58.7", "unit": "g"},
            {"key": "fat", "value": "7.0", "unit": "g"},
        ],
    }


def test_family_ingredient_create_and_list_include_latest_composition(
    db_session: Session,
) -> None:
    family = Family(name="Ingredient family", timezone="Europe/Lisbon")
    db_session.add(family)
    db_session.flush()

    response = _request(
        db_session,
        "POST",
        f"/api/families/{family.id}/ingredients",
        json={
            "name": "Flocos de aveia",
            "brand": "Casa",
            "description": "Aveia integral",
            "composition": _composition(),
        },
    )

    assert response.status_code == 201
    created = response.json()
    assert created["family_id"] == str(family.id)
    assert created["scope"] == "family"
    assert created["editable"] is True
    assert created["name"] == "Flocos de aveia"
    assert created["is_active"] is True
    assert created["recipe_usage_count"] == 0
    assert created["catalog_key"].startswith(f"family:{family.id}:ingredient:")
    assert created["latest_composition"]["reference_quantity"] == "100.0000"
    assert created["latest_composition"]["reference_unit"] == "g"
    assert created["latest_composition"]["energy_kcal"] == "370.0000"
    assert [item["key"] for item in created["latest_composition"]["nutrients"]] == [
        "carbohydrate",
        "fat",
        "protein",
    ]

    listed = _request(
        db_session,
        "GET",
        f"/api/families/{family.id}/ingredients",
        params={"q": "aveia"},
    )
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [created["id"]]


def test_shared_ingredients_are_visible_but_not_family_editable(db_session: Session) -> None:
    family = Family(name="Shared catalogue family", timezone="Europe/Lisbon")
    shared = FoodItem(
        family_id=None,
        catalog_key="shared:ingredient:tomato",
        name="Tomate partilhado",
        food_kind="ingredient",
        source="catalogue",
        is_active=True,
    )
    db_session.add_all([family, shared])
    db_session.flush()

    listed = _request(db_session, "GET", f"/api/families/{family.id}/ingredients")
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    item = listed.json()[0]
    assert item["id"] == str(shared.id)
    assert item["family_id"] is None
    assert item["scope"] == "shared"
    assert item["editable"] is False
    assert item["recipe_usage_count"] == 0

    detail = _request(
        db_session,
        "GET",
        f"/api/families/{family.id}/ingredients/{shared.id}",
    )
    assert detail.status_code == 200
    assert detail.json()["scope"] == "shared"

    update = _request(
        db_session,
        "PATCH",
        f"/api/families/{family.id}/ingredients/{shared.id}",
        json={"name": "Tentativa"},
    )
    assert update.status_code == 404


def test_ingredient_recipe_usage_count_is_family_visible_scope(db_session: Session) -> None:
    family_a = Family(name="Usage A", timezone="Europe/Lisbon")
    family_b = Family(name="Usage B", timezone="Europe/Lisbon")
    shared = FoodItem(
        family_id=None,
        catalog_key="shared:ingredient:usage",
        name="Ingrediente usado",
        food_kind="ingredient",
        source="catalogue",
        is_active=True,
    )
    db_session.add_all([family_a, family_b, shared])
    db_session.flush()

    for family in (family_a, family_b):
        created = _request(
            db_session,
            "POST",
            f"/api/families/{family.id}/recipes",
            json={
                "name": f"Receita {family.name}",
                "serving_count": "1",
                "ingredients": [
                    {"food_item_id": str(shared.id), "quantity": "100", "unit": "g"}
                ],
            },
        )
        assert created.status_code == 201

    listed_a = _request(db_session, "GET", f"/api/families/{family_a.id}/ingredients")
    assert listed_a.status_code == 200
    assert listed_a.json()[0]["recipe_usage_count"] == 1

    listed_b = _request(db_session, "GET", f"/api/families/{family_b.id}/ingredients")
    assert listed_b.status_code == 200
    assert listed_b.json()[0]["recipe_usage_count"] == 1


def test_ingredient_update_creates_new_composition_version(db_session: Session) -> None:
    family = Family(name="Version family", timezone="Europe/Lisbon")
    db_session.add(family)
    db_session.flush()

    created = _request(
        db_session,
        "POST",
        f"/api/families/{family.id}/ingredients",
        json={"name": "Iogurte", "composition": _composition("60")},
    ).json()

    response = _request(
        db_session,
        "PATCH",
        f"/api/families/{family.id}/ingredients/{created['id']}",
        json={
            "name": "Iogurte natural",
            "composition": _composition("64"),
        },
    )

    assert response.status_code == 200
    updated = response.json()
    assert updated["name"] == "Iogurte natural"
    assert updated["latest_composition"]["energy_kcal"] == "64.0000"
    assert updated["latest_composition"]["data_version"] != created["latest_composition"][
        "data_version"
    ]

    composition_count = db_session.scalar(
        select(func.count())
        .select_from(FoodCompositionSnapshot)
        .join(FoodItem)
        .where(FoodItem.id == uuid.UUID(created["id"]))
    )
    assert composition_count == 2


def test_ingredient_delete_is_soft_and_inactive_can_be_restored(db_session: Session) -> None:
    family = Family(name="Soft delete family", timezone="Europe/Lisbon")
    db_session.add(family)
    db_session.flush()

    created = _request(
        db_session,
        "POST",
        f"/api/families/{family.id}/ingredients",
        json={"name": "Cenoura"},
    ).json()

    deleted = _request(
        db_session,
        "DELETE",
        f"/api/families/{family.id}/ingredients/{created['id']}",
    )
    assert deleted.status_code == 204

    active = _request(db_session, "GET", f"/api/families/{family.id}/ingredients")
    assert active.json() == []

    inactive = _request(
        db_session,
        "GET",
        f"/api/families/{family.id}/ingredients",
        params={"include_inactive": "true"},
    )
    assert inactive.status_code == 200
    assert inactive.json()[0]["is_active"] is False

    restored = _request(
        db_session,
        "PATCH",
        f"/api/families/{family.id}/ingredients/{created['id']}",
        json={"is_active": True},
    )
    assert restored.status_code == 200
    assert restored.json()["is_active"] is True


def test_ingredient_endpoints_preserve_family_isolation(db_session: Session) -> None:
    family_a = Family(name="Family A", timezone="Europe/Lisbon")
    family_b = Family(name="Family B", timezone="Europe/Lisbon")
    db_session.add_all([family_a, family_b])
    db_session.flush()

    created = _request(
        db_session,
        "POST",
        f"/api/families/{family_a.id}/ingredients",
        json={"name": "Tomate"},
    ).json()

    response = _request(
        db_session,
        "GET",
        f"/api/families/{family_b.id}/ingredients/{created['id']}",
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Ingredient not found"

    list_b = _request(db_session, "GET", f"/api/families/{family_b.id}/ingredients")
    assert list_b.status_code == 200
    assert list_b.json() == []


def test_ingredient_composition_validation_rejects_invalid_values(db_session: Session) -> None:
    family = Family(name="Validation family", timezone="Europe/Lisbon")
    db_session.add(family)
    db_session.flush()

    negative = _request(
        db_session,
        "POST",
        f"/api/families/{family.id}/ingredients",
        json={
            "name": "Invalid",
            "composition": {
                "reference_quantity": "100",
                "reference_unit": "g",
                "energy_kcal": "-1",
            },
        },
    )
    assert negative.status_code == 422

    duplicate = _request(
        db_session,
        "POST",
        f"/api/families/{family.id}/ingredients",
        json={
            "name": "Duplicate nutrients",
            "composition": {
                "reference_quantity": "100",
                "reference_unit": "g",
                "nutrients": [
                    {"key": "protein", "value": "1", "unit": "g"},
                    {"key": "Protein", "value": "2", "unit": "g"},
                ],
            },
        },
    )
    assert duplicate.status_code == 422
