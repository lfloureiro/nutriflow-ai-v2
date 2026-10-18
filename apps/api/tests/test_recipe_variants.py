from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.db.session import get_db
from app.main import app
from app.models import (
    Family,
    FoodCompositionSnapshot,
    FoodItem,
    NutritionConstraint,
    Person,
    Recipe,
    RecipeIngredient,
)
from app.services.pantry_shopping import refresh_shopping_list
from app.services.recipe_nutrition import build_recipe_composition
from app.services.recipe_variant_integrity import recipe_fingerprint


@pytest.fixture
def client(db_session):
    def override():
        yield db_session

    app.dependency_overrides[get_db] = override
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def pilot(db_session):
    family = Family(name="Variant pilot", timezone="Europe/Lisbon")
    other = Family(name="Private")
    db_session.add_all([family, other])
    db_session.flush()
    people = [Person(family_id=family.id, first_name=n) for n in ("Ana", "Bruno")]
    foods = []
    for key, name, energy in [
        ("pasta", "Massa de trigo", 350),
        ("onion", "Cebola", 40),
        ("rice", "Massa de arroz", 360),
        ("chives", "Cebolinho", 30),
    ]:
        food = FoodItem(catalog_key=f"pilot:{key}", name=name, food_kind="ingredient")
        food.compositions.append(
            FoodCompositionSnapshot(
                reference_quantity=Decimal(100),
                reference_unit="g",
                energy_kcal=Decimal(energy),
                data_version="pilot-v1",
                source="test",
                effective_at=datetime(2020, 1, 1, tzinfo=UTC),
            )
        )
        foods.append(food)
    recipe = Recipe(
        family_id=family.id,
        recipe_key="pilot:base",
        name="Esparguete da família",
        serving_count=Decimal(2),
        source="test",
        suitable_meal_types=["lunch", "dinner"],
    )
    db_session.add_all([*people, *foods, recipe])
    db_session.flush()
    recipe.ingredients = [
        RecipeIngredient(food_item=foods[0], quantity=Decimal(100), unit="g", sort_order=0),
        RecipeIngredient(food_item=foods[1], quantity=Decimal(40), unit="g", sort_order=1),
    ]
    db_session.flush()
    build_recipe_composition(recipe)
    db_session.flush()
    for food in foods[:2]:
        db_session.add(
            NutritionConstraint(
                person_id=people[0].id,
                constraint_type="exclusion",
                target_type="food_item",
                target_key=food.catalog_key,
                operator="exclude",
                is_mandatory=True,
                source="user",
            )
        )
    db_session.flush()
    payload = {
        "base_recipe_id": str(recipe.id),
        "name": "Arroz e cebolinho",
        "serving_count": "2",
        "operations": [
            {
                "recipe_ingredient_id": str(i.id),
                "replacement_food_item_id": str(f.id),
                "quantity": q,
                "unit": "g",
                "preparation": "Test preparation",
            }
            for i, f, q in zip(recipe.ingredients, foods[2:], ["120", "10"], strict=True)
        ],
    }
    context = {
        "expected_version": 1,
        "planning_date": "2030-01-07",
        "meal_type": "dinner",
        "participants": [{"person_id": str(p.id), "quantity": "1"} for p in people],
    }
    return family, other, people, foods, recipe, payload, context


def test_variant_complete_composition_activation_and_shopping(client, db_session, pilot):
    family, _, people, foods, base, payload, context = pilot
    path = f"/api/families/{family.id}/recipe-variants"
    before = recipe_fingerprint(base)
    response = client.post(path, json=payload)
    assert response.status_code == 201, response.text
    variant = response.json()
    assert variant["issues"] == []
    assert Decimal(variant["energy_per_serving"]) == Decimal("217.5")
    assert variant["status"] == "draft"
    assert recipe_fingerprint(base) == before
    assert not db_session.get(Recipe, variant["recipe_id"]).is_active
    checked = client.post(path + f"/{variant['id']}/validate", json=context)
    assert checked.status_code == 200, checked.text
    assert checked.json()["eligible"] is True, checked.text
    active = client.post(path + f"/{variant['id']}/activate", json=context)
    assert active.status_code == 200, active.text
    assert active.json()["status"] == "active"
    reviews = client.get(f"/api/families/{family.id}/recipe-adaptations").json()
    assert len(reviews) == 1
    assert len(reviews[0]["active_variants"][0]["operations"]) == 2
    assert reviews[0]["active_variants"][0]["recipe_id"] == variant["recipe_id"]
    assert client.post(path + f"/{variant['id']}/activate", json=context).status_code == 409
    plan = client.post(
        f"/api/families/{family.id}/meal-plan",
        json={
            "date": "2030-01-07",
            "meal_type": "dinner",
            "local_time": "19:00",
            "recipe_id": variant["recipe_id"],
            "participants": [
                {"person_id": str(p.id), "quantity": "1", "unit": "serving"} for p in people
            ],
        },
    )
    assert plan.status_code == 201, plan.text
    shopping = refresh_shopping_list(db_session, family, start_date=date(2030, 1, 7), days=7)
    amounts = {
        str(i.food_item_id): i.quantity for i in shopping.items if i.item_source == "automatic"
    }
    assert str(foods[0].id) not in amounts and str(foods[1].id) not in amounts
    assert amounts[str(foods[2].id)] == Decimal(120)
    assert amounts[str(foods[3].id)] == Decimal(10)
    assert recipe_fingerprint(base) == before


def test_partial_variant_and_second_person_conflict_cannot_activate(client, db_session, pilot):
    family, _, people, foods, _, payload, context = pilot
    path = f"/api/families/{family.id}/recipe-variants"
    partial = client.post(path, json={**payload, "operations": payload["operations"][:1]}).json()
    result = client.post(path + f"/{partial['id']}/validate", json=context).json()
    assert result["eligible"] is False
    assert client.post(path + f"/{partial['id']}/activate", json=context).status_code == 422
    complete = client.post(path, json=payload).json()
    db_session.add(
        NutritionConstraint(
            person_id=people[1].id,
            constraint_type="exclusion",
            target_type="food_item",
            target_key=foods[2].catalog_key,
            operator="exclude",
            is_mandatory=True,
            source="user",
        )
    )
    db_session.flush()
    result = client.post(path + f"/{complete['id']}/validate", json=context).json()
    assert result["participants"][0]["eligible"] is True
    assert result["participants"][1]["eligible"] is False
    assert client.post(path + f"/{complete['id']}/activate", json=context).status_code == 422
    assert not db_session.get(Recipe, complete["recipe_id"]).is_active


def test_variant_family_scope_duplicates_missing_evidence_and_immutability(
    client, db_session, pilot
):
    family, other, _, _foods, base, payload, context = pilot
    path = f"/api/families/{family.id}/recipe-variants"
    assert (
        client.post(
            path, json={**payload, "operations": [payload["operations"][0]] * 2}
        ).status_code
        == 422
    )
    assert client.post(f"/api/families/{other.id}/recipe-variants", json=payload).status_code == 404
    missing = FoodItem(
        family_id=family.id, catalog_key="pilot:no-composition", name="Unknown label"
    )
    db_session.add(missing)
    db_session.flush()
    operations = [
        {**payload["operations"][0], "replacement_food_item_id": str(missing.id)},
        payload["operations"][1],
    ]
    variant = client.post(path, json={**payload, "operations": operations}).json()
    assert variant["issues"]
    assert client.post(path + f"/{variant['id']}/activate", json=context).status_code == 422
    assert client.get(f"/api/families/{other.id}/recipe-variants").json() == []
    assert (
        client.patch(
            f"/api/families/{family.id}/recipes/{variant['recipe_id']}", json={"is_active": True}
        ).status_code
        == 422
    )
    assert (
        client.delete(f"/api/families/{family.id}/recipes/{variant['recipe_id']}").status_code
        == 422
    )
    assert db_session.get(Recipe, base.id).is_active


def test_variant_base_and_label_changes_force_new_revision(client, db_session, pilot):
    family, _, _, foods, base, payload, context = pilot
    path = f"/api/families/{family.id}/recipe-variants"
    variant = client.post(path, json=payload).json()
    base.ingredients[0].quantity = Decimal(101)
    db_session.flush()
    checked = client.post(path + f"/{variant['id']}/validate", json=context).json()
    assert not checked["eligible"] and any("base_recipe_changed" in i for i in checked["issues"])
    revision = client.post(path, json={**payload, "revises_variant_id": variant["id"]}).json()
    assert revision["revision"] == 2 and revision["issues"] == []
    assert (
        client.post(path, json={**payload, "revises_variant_id": variant["id"]}).status_code == 409
    )
    foods[2].compositions.append(
        FoodCompositionSnapshot(
            reference_quantity=100,
            reference_unit="g",
            energy_kcal=400,
            data_version="new-label",
            source="test",
            effective_at=datetime(2027, 1, 1, tzinfo=UTC),
        )
    )
    db_session.flush()
    checked = client.post(path + f"/{revision['id']}/validate", json=context).json()
    assert not checked["eligible"] and any(
        "variant_evidence_changed" in i for i in checked["issues"]
    )


def test_fingerprint_normalizes_decimal_storage_scale(pilot):
    *_, base, _, _ = pilot
    before = recipe_fingerprint(base)
    base.ingredients[0].quantity = Decimal("100.0000")
    base.serving_count = Decimal("2.00")
    assert recipe_fingerprint(base) == before


def test_variant_revision_retires_previous_without_rewriting_planned_recipe(
    client, db_session, pilot
):
    family, _, people, foods, _, payload, context = pilot
    path = f"/api/families/{family.id}/recipe-variants"
    first = client.post(path, json=payload).json()
    assert client.post(path + f"/{first['id']}/activate", json=context).status_code == 200
    plan = client.post(
        f"/api/families/{family.id}/meal-plan",
        json={
            "date": "2030-01-07",
            "meal_type": "dinner",
            "local_time": "19:00",
            "recipe_id": first["recipe_id"],
            "participants": [{"person_id": str(p.id)} for p in people],
        },
    )
    assert plan.status_code == 201, plan.text
    updated_ops = [{**payload["operations"][0], "quantity": "130"}, payload["operations"][1]]
    second = client.post(
        path, json={**payload, "revises_variant_id": first["id"], "operations": updated_ops}
    ).json()
    assert client.post(path + f"/{second['id']}/activate", json=context).status_code == 200
    old = db_session.get(Recipe, first["recipe_id"])
    assert not old.is_active
    assert old.ingredients[0].quantity == Decimal(120)
    saved = client.get(f"/api/families/{family.id}/meal-plan?start_date=2030-01-07&days=7").json()
    entry = next(
        slot["meals"][0] for slot in saved["days"][0]["slots"] if slot["meal_type"] == "dinner"
    )
    assert entry["recipe_id"] == first["recipe_id"] and len(entry["variant_changes"]) == 2
    shopping = refresh_shopping_list(db_session, family, start_date=date(2030, 1, 7), days=7)
    rice = next(i for i in shopping.items if str(i.food_item_id) == str(foods[2].id))
    assert rice.quantity == Decimal(120)


def test_weekly_planner_selects_complete_variant_and_rechecks_changed_rules(
    client, db_session, pilot
):
    from app.models import DailyNutritionState

    family, _, people, foods, base, payload, context = pilot
    path = f"/api/families/{family.id}/recipe-variants"
    variant = client.post(path, json=payload).json()
    assert client.post(path + f"/{variant['id']}/activate", json=context).status_code == 200
    recipe = db_session.get(Recipe, variant["recipe_id"])
    for p in people:
        db_session.add(
            DailyNutritionState(
                person_id=p.id,
                state_date=date(2030, 1, 7),
                timezone="Europe/Lisbon",
                energy_consumed_kcal=Decimal(0),
                energy_planned_kcal=Decimal(0),
                energy_remaining_min_kcal=Decimal(0),
                energy_remaining_max_kcal=Decimal(5000),
                calculation_version="test",
                computed_at=datetime(2030, 1, 7, tzinfo=UTC),
            )
        )
    db_session.flush()
    request = {
        "person_ids": [str(p.id) for p in people],
        "slots": [
            {
                "slot_key": "dinner",
                "planning_date": "2030-01-07",
                "scheduled_at": "2030-01-07T19:00:00Z",
                "meal_type": "dinner",
                "candidates": [
                    {
                        "candidate_kind": "recipe",
                        "composition_id": str(r.compositions[-1].id),
                        "quantity": "1",
                        "quantity_unit": "serving",
                    }
                    for r in [base, recipe]
                ],
            }
        ],
    }
    weekly = f"/api/families/{family.id}/weekly-planning"
    response = client.post(weekly + "/proposals", json=request)
    assert response.status_code == 201, response.text
    choice = response.json()["selected_plan"]["choices"][0]
    assert choice["recipe_id"] == str(recipe.id)
    assert len(choice["variant_changes"]) == 2
    db_session.add(
        NutritionConstraint(
            person_id=people[1].id,
            constraint_type="exclusion",
            target_type="food_item",
            target_key=foods[2].catalog_key,
            operator="exclude",
            is_mandatory=True,
            source="user",
        )
    )
    db_session.flush()
    result = client.post(
        weekly + "/plan",
        json={
            **request,
            "expected_choices": [{"slot_key": "dinner", "candidate_key": recipe.recipe_key}],
        },
    )
    assert result.status_code == 409, result.text
