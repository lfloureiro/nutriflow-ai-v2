from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.main import app
from app.models.family import Family


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


def test_ingredient_nutrition_edit_recalculates_referencing_recipe(db_session: Session) -> None:
    family = Family(name="Propagation family", timezone="Europe/Lisbon")
    db_session.add(family)
    db_session.flush()

    ingredient = _request(
        db_session,
        "POST",
        f"/api/families/{family.id}/ingredients",
        json={
            "name": "Ingrediente base",
            "composition": {
                "reference_quantity": "100",
                "reference_unit": "g",
                "energy_kcal": "100",
            },
        },
    ).json()

    recipe = _request(
        db_session,
        "POST",
        f"/api/families/{family.id}/recipes",
        json={
            "name": "Receita dependente",
            "serving_count": "2",
            "yield_quantity": "200",
            "yield_unit": "g",
            "ingredients": [
                {"food_item_id": ingredient["id"], "quantity": "200", "unit": "g"}
            ],
        },
    ).json()
    assert Decimal(recipe["latest_composition"]["energy_kcal"]) == Decimal("200")

    updated_ingredient = _request(
        db_session,
        "PATCH",
        f"/api/families/{family.id}/ingredients/{ingredient['id']}",
        json={
            "composition": {
                "reference_quantity": "100",
                "reference_unit": "g",
                "energy_kcal": "150",
            }
        },
    )
    assert updated_ingredient.status_code == 200

    refreshed_recipe = _request(
        db_session,
        "GET",
        f"/api/families/{family.id}/recipes/{recipe['id']}",
    )
    assert refreshed_recipe.status_code == 200
    body = refreshed_recipe.json()
    assert Decimal(body["latest_composition"]["energy_kcal"]) == Decimal("300")
    assert Decimal(body["latest_composition"]["energy_per_serving_kcal"]) == Decimal("150")
