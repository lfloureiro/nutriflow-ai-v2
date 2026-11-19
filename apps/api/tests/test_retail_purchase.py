import uuid
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models import Family, FoodItem, Person, Recipe
from app.models.planning_workspace import RetailAlternative
from app.retail_alternatives_seed import import_retail_observations
from tests.test_pantry_shopping_api import _ingredient, _recipe, _request


@pytest.fixture
def retail_context(db_session):
    family = Family(name="Retail fixture", timezone="Europe/Lisbon")
    other = Family(name="Other retail fixture")
    people = [Person(family=family, first_name=n) for n in ("Ana", "Bruno")]
    db_session.add_all([family, other, *people])
    db_session.flush()
    import_retail_observations(db_session)
    path = f"/api/families/{family.id}"
    products = _request(db_session, "GET", path + "/retail-alternatives").json()
    pasta = next(p for p in products if "2749257.html" in p["product_url"])
    confirmed = _request(
        db_session,
        "POST",
        path + f"/retail-alternatives/{pasta['id']}/confirm-ingredient",
        json={"expected_fingerprint": pasta["evidence_fingerprint"], "label_reviewed": True},
    )
    assert confirmed.status_code == 200, confirmed.text
    return family, other, people, path, pasta, confirmed.json()["food_item_id"]


def _effective_variant_shopping(db, context):
    family, _, people, path, _product, food_id = context
    original = _ingredient(db, family, "Original wheat")
    base = _recipe(db, family, original["id"])
    base_model = db.get(Recipe, uuid.UUID(base["id"]))
    draft = _request(
        db,
        "POST",
        path + "/recipe-variants",
        json={
            "base_recipe_id": base["id"],
            "name": "Reviewed product variant",
            "serving_count": "2",
            "operations": [
                {
                    "recipe_ingredient_id": str(base_model.ingredients[0].id),
                    "replacement_food_item_id": food_id,
                    "quantity": "1200",
                    "unit": "g",
                    "preparation": "Test preparation",
                }
            ],
        },
    )
    assert draft.status_code == 201, draft.text
    variant = draft.json()
    active = _request(
        db,
        "POST",
        path + f"/recipe-variants/{variant['id']}/activate",
        json={
            "expected_version": 1,
            "planning_date": "2030-01-07",
            "meal_type": "dinner",
            "participants": [{"person_id": str(p.id), "quantity": "1"} for p in people],
        },
    )
    assert active.status_code == 200, active.text
    planned = _request(
        db,
        "POST",
        path + "/meal-plan",
        json={
            "date": "2030-01-07",
            "local_time": "20:00",
            "meal_type": "dinner",
            "recipe_id": variant["recipe_id"],
            "participants": [
                {"person_id": str(p.id), "quantity": "1", "unit": "serving"} for p in people
            ],
        },
    )
    assert planned.status_code == 201, planned.text
    stock = _request(
        db,
        "POST",
        path + "/pantry",
        json={"food_item_id": food_id, "quantity_available": "100", "unit": "g"},
    )
    assert stock.status_code == 201
    shopping = _request(
        db, "POST", path + "/shopping-list/refresh", json={"start_date": "2030-01-07", "days": 7}
    )
    assert shopping.status_code == 200, shopping.text
    item = shopping.json()["items"][0]
    assert item["food_item_id"] == food_id
    assert item["food_item_id"] != original["id"]
    assert Decimal(item["quantity"]) == 1100
    return item, variant, original


def _select(db, path, product, item):
    return _request(
        db,
        "PUT",
        path + f"/shopping-list/items/{item['id']}/product",
        json={
            "expected_version": item["version"],
            "retail_product_id": product["id"],
            "expected_fingerprint": product["evidence_fingerprint"],
        },
    )


def test_confirmed_product_is_family_scoped_idempotent_and_preserves_unknown_nutrients(
    db_session, retail_context
):
    family, other, _, path, product, food_id = retail_context
    again = _request(
        db_session,
        "POST",
        path + f"/retail-alternatives/{product['id']}/confirm-ingredient",
        json={"expected_fingerprint": product["evidence_fingerprint"], "label_reviewed": True},
    )
    assert again.status_code == 200 and again.json()["food_item_id"] == food_id
    db_session.expire_all()
    read = _request(db_session, "GET", path + "/retail-alternatives").json()
    assert next(p for p in read if p["id"] == product["id"])["confirmed_food_item_id"] == food_id
    food = db_session.get(FoodItem, uuid.UUID(food_id))
    assert food.family_id == family.id
    catalogue = _request(db_session, "GET", path + "/ingredients").json()
    assert food_id in {row["id"] for row in catalogue}
    assert "sodium" not in {n.nutrient_key for n in food.compositions[-1].nutrients}
    other_products = _request(
        db_session, "GET", f"/api/families/{other.id}/retail-alternatives"
    ).json()
    assert all(p["confirmed_food_item_id"] is None for p in other_products)
    assert all(food_id not in p["applicable_food_item_ids"] for p in other_products)


def test_product_label_requires_review_and_complete_nonzero_evidence(db_session, retail_context):
    _, _, _, path, _, _ = retail_context
    products = _request(db_session, "GET", path + "/retail-alternatives").json()
    flour = next(p for p in products if "3452448.html" in p["product_url"])
    url = path + f"/retail-alternatives/{flour['id']}/confirm-ingredient"
    data = {"expected_fingerprint": flour["evidence_fingerprint"], "label_reviewed": True}
    assert (
        _request(db_session, "POST", url, json={**data, "label_reviewed": False}).status_code == 422
    )
    assert _request(db_session, "POST", url, json=data).status_code == 422
    assert (
        _request(
            db_session, "POST", url, json={**data, "expected_fingerprint": "0" * 64}
        ).status_code
        == 409
    )


def test_variant_pantry_and_pack_rounding_use_only_actual_ingredient(db_session, retail_context):
    _, other, _, path, product, _ = retail_context
    item, _, _ = _effective_variant_shopping(db_session, retail_context)
    response = _select(db_session, path, product, item)
    assert response.status_code == 200, response.text
    selected = response.json()["items"][0]
    choice = selected["product_selection"]
    assert choice["status"] == "confirmed"
    assert choice["package_count"] == 3
    assert Decimal(choice["total_quantity"]) == 1500
    assert Decimal(choice["excess_quantity"]) == 400
    assert Decimal(choice["estimated_total"]) == Decimal("5.25")
    assert _select(db_session, path, product, item).status_code == 409
    assert _select(db_session, f"/api/families/{other.id}", product, selected).status_code == 404
    cleared = _request(
        db_session,
        "PUT",
        path + f"/shopping-list/items/{item['id']}/product",
        json={"expected_version": selected["version"], "retail_product_id": None},
    )
    assert cleared.status_code == 200 and cleared.json()["items"][0]["product_selection"] is None


def test_original_ingredient_cannot_buy_substitute_and_changed_quantities_need_review(
    db_session, retail_context
):
    _, _, _, path, product, _ = retail_context
    item, _, original = _effective_variant_shopping(db_session, retail_context)
    selected = _select(db_session, path, product, item).json()["items"][0]
    changed = _request(
        db_session,
        "PATCH",
        path + f"/shopping-list/items/{item['id']}",
        json={"quantity": "1.1", "unit": "kg"},
    )
    assert changed.status_code == 200
    updated = changed.json()["items"][0]
    assert updated["product_selection"]["status"] == "needs_review"
    assert updated["product_selection"]["package_count"] is None
    recalculated = _select(db_session, path, product, updated)
    assert recalculated.status_code == 200, recalculated.text
    assert recalculated.json()["items"][0]["product_selection"]["package_count"] == 3
    # A proposal link on the original food is not a confirmed product identity.
    from app.models.shopping_list import ShoppingListItem

    model = db_session.get(ShoppingListItem, uuid.UUID(item["id"]))
    model.food_item_id = uuid.UUID(original["id"])
    model.product_confirmation = None
    model.product_selection = None
    db_session.commit()
    wrong = _select(db_session, path, product, {**selected, "version": model.version})
    assert wrong.status_code == 422 and "exact confirmed ingredient" in wrong.json()["detail"]


def test_changed_label_invalidates_packages_and_new_variant_use(db_session, retail_context):
    _, _, _, path, product, _ = retail_context
    item, variant, _ = _effective_variant_shopping(db_session, retail_context)
    selected = _select(db_session, path, product, item)
    assert selected.status_code == 200, selected.text
    row = db_session.get(RetailAlternative, uuid.UUID(product["id"]))
    row.ingredient_summary += " Updated ingredients."
    db_session.commit()
    read = _request(db_session, "GET", path + "/shopping-list").json()["items"][0]
    assert read["product_selection"]["status"] == "needs_review"
    assert read["product_selection"]["package_count"] is None
    current = _request(
        db_session, "GET", path + f"/recipe-variants?base_recipe_id={variant['base_recipe_id']}"
    )
    assert any("retail_label_changed" in issue for issue in current.json()[0]["issues"])
    assert _select(db_session, path, product, read).status_code == 409


def test_package_preview_is_read_only_and_mass_volume_never_assume_density(
    db_session, retail_context
):
    from fastapi import HTTPException

    from app.models.shopping_list import ShoppingListItem
    from app.services.retail_purchase import package_amounts

    _, _, _, path, product, _ = retail_context
    item, _, _ = _effective_variant_shopping(db_session, retail_context)
    data = {
        "expected_version": item["version"],
        "retail_product_id": product["id"],
        "expected_fingerprint": product["evidence_fingerprint"],
    }
    preview = _request(
        db_session, "POST", path + f"/shopping-list/items/{item['id']}/product-preview", json=data
    )
    assert preview.status_code == 200 and preview.json()["package_count"] == 3
    model = db_session.get(ShoppingListItem, uuid.UUID(item["id"]))
    assert model.product_selection is None and model.version == item["version"]
    retail = db_session.get(RetailAlternative, uuid.UUID(product["id"]))
    with pytest.raises(HTTPException, match="incompatible"):
        package_amounts(Decimal(100), "ml", retail)


def test_stock_change_requires_refresh_and_new_confirmation(db_session, retail_context):
    from app.models.pantry_stock import PantryStockLot

    _, _, _, path, product, food_id = retail_context
    item, _, _ = _effective_variant_shopping(db_session, retail_context)
    assert _select(db_session, path, product, item).status_code == 200
    lot = db_session.scalar(
        select(PantryStockLot).where(PantryStockLot.food_item_id == uuid.UUID(food_id))
    )
    lot.quantity_available = Decimal(700)
    db_session.commit()
    old = _request(db_session, "GET", path + "/shopping-list").json()["items"][0]
    assert "shopping_needs_refresh" in old["product_selection"]["issues"]
    assert _select(db_session, path, product, old).status_code == 409
    refreshed = _request(
        db_session,
        "POST",
        path + "/shopping-list/refresh",
        json={"start_date": "2030-01-07", "days": 7},
    ).json()["items"][0]
    assert Decimal(refreshed["quantity"]) == 500
    assert refreshed["product_selection"]["status"] == "needs_review"
    response = _select(db_session, path, product, refreshed)
    assert response.status_code == 200, response.text
    assert response.json()["items"][0]["product_selection"]["package_count"] == 1


def test_purchased_product_keeps_historical_packages_and_cannot_be_reselected(
    db_session, retail_context
):
    _, _, _, path, product, _ = retail_context
    item, _, _ = _effective_variant_shopping(db_session, retail_context)
    assert _select(db_session, path, product, item).status_code == 200
    purchased = _request(
        db_session,
        "PATCH",
        path + f"/shopping-list/items/{item['id']}",
        json={"status": "purchased"},
    ).json()["items"][0]
    retail = db_session.get(RetailAlternative, uuid.UUID(product["id"]))
    retail.pack_quantity = Decimal(200)
    db_session.commit()
    read = _request(db_session, "GET", path + "/shopping-list").json()["items"][0]
    assert read["product_selection"]["package_count"] == 3
    assert Decimal(read["product_selection"]["pack_quantity"]) == 500
    assert _select(db_session, path, product, purchased).status_code == 409
