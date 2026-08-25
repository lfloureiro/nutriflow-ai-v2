import uuid
from datetime import UTC, datetime
from decimal import Decimal

from fastapi.testclient import TestClient
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


def _ingredient(
    family: Family,
    *,
    name: str,
    energy_per_100g: str | None,
) -> FoodItem:
    item = FoodItem(
        family=family,
        catalog_key=f"test:practical:{uuid.uuid4()}",
        name=name,
        food_kind="ingredient",
        source="test",
        is_active=True,
    )
    if energy_per_100g is not None:
        item.compositions.append(
            FoodCompositionSnapshot(
                reference_quantity=Decimal(100),
                reference_unit="g",
                energy_kcal=Decimal(energy_per_100g),
                data_version="test-v1",
                source="test",
                effective_at=datetime.now(UTC),
            )
        )
    return item


def test_new_recipe_is_classified_and_gets_planning_energy_automatically(
    db_session: Session,
) -> None:
    family = Family(name="Practical recipe family", timezone="Europe/Lisbon")
    turkey = _ingredient(family, name="Bifes de peru", energy_per_100g="140")
    margarine = _ingredient(family, name="Margarina", energy_per_100g=None)
    db_session.add_all([family, turkey, margarine])
    db_session.flush()

    response = _request(
        db_session,
        "POST",
        f"/api/families/{family.id}/recipes",
        json={
            "name": "Bifes de peru com limão",
            "ingredients": [
                {"food_item_id": str(turkey.id), "quantity": "800", "unit": "g"},
                {"food_item_id": str(margarine.id), "quantity": "100", "unit": "g"},
            ],
        },
    )

    assert response.status_code == 201
    body = response.json()
    composition = body["latest_composition"]
    profile = composition["practical_profile"]

    assert composition["energy_kcal"] is not None
    assert composition["energy_per_serving_kcal"] is not None
    assert composition["evidence"] == "ingredient_estimated"
    assert composition["serving_count_estimated"] is True
    assert composition["energy_confidence"] == "low"
    assert profile["primary_protein"] == "Bifes de peru"
    assert profile["primary_carbohydrate"] is None
    assert profile["energy_load_signal"] == "moderate"
    assert "carb_light" in profile["balance_signals"]
