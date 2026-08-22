import uuid
from datetime import UTC, datetime
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.main import app
from app.models.family import Family
from app.models.food_catalog import (
    FoodCompositionSnapshot,
    FoodItem,
    FoodNutrientComponent,
    RecipeCompositionSnapshot,
)


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


def _ingredient(
    family: Family,
    *,
    name: str,
    energy: str | None,
    protein: str | None = None,
) -> FoodItem:
    item = FoodItem(
        family=family,
        catalog_key=f"test:ingredient:{uuid.uuid4()}",
        name=name,
        food_kind="ingredient",
        source="test",
        is_active=True,
    )
    if energy is not None or protein is not None:
        composition = FoodCompositionSnapshot(
            reference_quantity=Decimal(100),
            reference_unit="g",
            energy_kcal=Decimal(energy) if energy is not None else None,
            data_version="test-v1",
            source="test",
            effective_at=datetime.now(UTC),
        )
        if protein is not None:
            composition.nutrients.append(
                FoodNutrientComponent(
                    nutrient_key="protein",
                    value=Decimal(protein),
                    unit="g",
                )
            )
        item.compositions.append(composition)
    return item


def test_recipe_create_calculates_total_and_per_serving_nutrition(db_session: Session) -> None:
    family = Family(name="Recipe family", timezone="Europe/Lisbon")
    oats = _ingredient(family, name="Aveia", energy="100", protein="10")
    yogurt = _ingredient(family, name="Iogurte", energy="200", protein="20")
    db_session.add_all([family, oats, yogurt])
    db_session.flush()

    response = _request(
        db_session,
        "POST",
        f"/api/families/{family.id}/recipes",
        json={
            "name": "Taça de aveia",
            "serving_count": "2",
            "yield_quantity": "150",
            "yield_unit": "g",
            "ingredients": [
                {"food_item_id": str(oats.id), "quantity": "50", "unit": "g"},
                {"food_item_id": str(yogurt.id), "quantity": "100", "unit": "g"},
            ],
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Taça de aveia"
    assert [item["food_item_name"] for item in body["ingredients"]] == ["Aveia", "Iogurte"]
    assert Decimal(body["latest_composition"]["energy_kcal"]) == Decimal(250)
    assert Decimal(body["latest_composition"]["energy_per_serving_kcal"]) == Decimal(125)
    assert body["nutrition_issues"] == []
    protein = body["latest_composition"]["nutrients"][0]
    assert protein["key"] == "protein"
    assert Decimal(protein["total_value"]) == Decimal(25)
    assert Decimal(protein["per_serving_value"]) == Decimal("12.5")


def test_recipe_missing_ingredient_composition_is_explicit(db_session: Session) -> None:
    family = Family(name="Missing evidence family", timezone="Europe/Lisbon")
    unknown = _ingredient(family, name="Ingrediente desconhecido", energy=None)
    db_session.add_all([family, unknown])
    db_session.flush()

    response = _request(
        db_session,
        "POST",
        f"/api/families/{family.id}/recipes",
        json={
            "name": "Receita incompleta",
            "serving_count": "1",
            "ingredients": [
                {"food_item_id": str(unknown.id), "quantity": "100", "unit": "g"}
            ],
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["latest_composition"]["energy_kcal"] is None
    assert body["nutrition_issues"]
    assert "no nutrition composition" in body["nutrition_issues"][0]


def test_recipe_update_appends_composition_and_soft_delete_hides_recipe(
    db_session: Session,
) -> None:
    family = Family(name="Recipe lifecycle family", timezone="Europe/Lisbon")
    ingredient = _ingredient(family, name="Arroz", energy="130", protein="3")
    db_session.add_all([family, ingredient])
    db_session.flush()

    created = _request(
        db_session,
        "POST",
        f"/api/families/{family.id}/recipes",
        json={
            "name": "Arroz simples",
            "serving_count": "2",
            "ingredients": [
                {"food_item_id": str(ingredient.id), "quantity": "200", "unit": "g"}
            ],
        },
    ).json()

    updated = _request(
        db_session,
        "PATCH",
        f"/api/families/{family.id}/recipes/{created['id']}",
        json={
            "ingredients": [
                {"food_item_id": str(ingredient.id), "quantity": "300", "unit": "g"}
            ]
        },
    )
    assert updated.status_code == 200
    assert Decimal(updated.json()["latest_composition"]["energy_kcal"]) == Decimal(390)

    snapshot_count = db_session.scalar(
        select(func.count())
        .select_from(RecipeCompositionSnapshot)
        .where(RecipeCompositionSnapshot.recipe_id == uuid.UUID(created["id"]))
    )
    assert snapshot_count == 2

    deleted = _request(
        db_session,
        "DELETE",
        f"/api/families/{family.id}/recipes/{created['id']}",
    )
    assert deleted.status_code == 204
    active = _request(db_session, "GET", f"/api/families/{family.id}/recipes")
    assert active.status_code == 200
    assert active.json() == []
