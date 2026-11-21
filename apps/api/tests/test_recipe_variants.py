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


def _saved_base_meal(client, db_session, pilot):
    from sqlalchemy import select

    family, _, people, _, base, _, _ = pilot
    constraints = list(db_session.scalars(select(NutritionConstraint)))
    for constraint in constraints:
        constraint.end_date = date(2029, 12, 31)
    db_session.flush()
    response = client.post(f"/api/families/{family.id}/meal-plan", json={
        "date": "2030-01-07", "meal_type": "dinner", "local_time": "20:00",
        "recipe_id": str(base.id), "participants": [{"person_id": str(p.id), "quantity": "1", "unit": "serving"} for p in people],
    })
    assert response.status_code == 201, response.text
    for constraint in constraints:
        constraint.end_date = None
    db_session.commit()
    return response.json()


def test_accept_variant_then_confirm_saved_meal_updates_actual_ingredients(client, db_session, pilot):
    family, _, people, foods, base, payload, context = pilot
    before = recipe_fingerprint(base)
    meal = _saved_base_meal(client, db_session, pilot)
    path = f"/api/families/{family.id}/recipe-variants"
    variant = client.post(path, json=payload).json()
    assert client.post(f"{path}/{variant['id']}/validate", json=context).json()["eligible"]
    active = client.post(f"{path}/{variant['id']}/activate", json=context).json()
    # Accepting ingredient changes alone must not rewrite the saved meal.
    agenda = client.get(f"/api/families/{family.id}/meal-plan", params={"start_date": "2030-01-07", "days": 1}).json()
    assert agenda["days"][0]["slots"][3]["meals"][0]["recipe_id"] == str(base.id)
    result = client.patch(f"/api/families/{family.id}/meal-plan/{meal['id']}", json={
        "expected_updated_at": meal["updated_at"], "recipe_id": active["recipe_id"],
        "participants": [{"person_id": str(p.id), "quantity": "1", "unit": "serving"} for p in people],
    })
    assert result.status_code == 200, result.text
    assert result.json()["recipe_id"] == active["recipe_id"]
    assert len(result.json()["variant_changes"]) == 2
    assert result.json()["local_time"] == "20:00:00"
    shopping = refresh_shopping_list(db_session, family, start_date=date(2030, 1, 7), days=7)
    amounts = {str(item.food_item_id): item.quantity for item in shopping.items if item.item_source == "automatic"}
    assert str(foods[0].id) not in amounts and str(foods[1].id) not in amounts
    assert amounts[str(foods[2].id)] == Decimal(120)
    assert recipe_fingerprint(base) == before


def test_meal_confirmation_rejects_stale_review_after_portions_changed(client, db_session, pilot):
    family, _, _, _, _, _, _ = pilot
    meal = _saved_base_meal(client, db_session, pilot)
    # A simple edit updates the concurrency token even if title/recipe stay the same.
    url = f"/api/families/{family.id}/meal-plan/{meal['id']}"
    changed = client.patch(url, json={"expected_updated_at": meal["updated_at"], "location": "Outro local"})
    assert changed.status_code == 200, changed.text
    assert changed.json()["updated_at"] != meal["updated_at"]
    stale = client.patch(url, json={"expected_updated_at": meal["updated_at"], "notes": "stale"})
    assert stale.status_code == 409
    assert "changed since review" in stale.json()["detail"]


def test_meal_confirmation_rechecks_restrictions_after_variant_acceptance(client, db_session, pilot):
    family, _, people, foods, base, payload, context = pilot
    meal = _saved_base_meal(client, db_session, pilot)
    path = f"/api/families/{family.id}/recipe-variants"
    variant = client.post(path, json=payload).json()
    active = client.post(f"{path}/{variant['id']}/activate", json=context).json()
    db_session.add(NutritionConstraint(person_id=people[1].id, constraint_type="exclusion", target_type="food_item", target_key=foods[2].catalog_key, operator="exclude", is_mandatory=True, source="user"))
    db_session.commit()
    result = client.patch(f"/api/families/{family.id}/meal-plan/{meal['id']}", json={
        "expected_updated_at": meal["updated_at"], "recipe_id": active["recipe_id"],
        "participants": [{"person_id": str(p.id), "quantity": "1", "unit": "serving"} for p in people],
    })
    assert result.status_code == 422, result.text
    agenda = client.get(f"/api/families/{family.id}/meal-plan", params={"start_date": "2030-01-07", "days": 1}).json()
    assert agenda["days"][0]["slots"][3]["meals"][0]["recipe_id"] == str(base.id)


def _incomplete_adaptation_draft(pilot, meal):
    _, _, people, _, base, _, _ = pilot
    return {"base_recipe_id": str(base.id), "meal_event_id": meal["id"], "planning_date": "2030-01-07", "meal_type": "dinner", "name": "Incomplete adaptation", "serving_count": "", "operations": [{"recipe_ingredient_id": str(base.ingredients[0].id), "replacement_food_item_id": None, "replacement_name": "Alternative still to identify", "quantity": "", "unit": "", "preparation": ""}], "participants": [{"person_id": str(person.id), "quantity": "1", "unit": "serving"} for person in people], "decisions": {str(base.ingredients[0].id): "accepted"}}


def test_incomplete_draft_persists_unknowns_without_altering_meal_or_creating_variant(client, db_session, pilot):
    from sqlalchemy import func, select

    from app.models.recipe_variant import FamilyRecipeVariant

    family, _, _, _, base, _, _ = pilot
    meal = _saved_base_meal(client, db_session, pilot)
    base.serving_count = None
    db_session.commit()
    data = _incomplete_adaptation_draft(pilot, meal)
    path = f"/api/families/{family.id}/meal-adaptation-drafts"
    result = client.post(path, json=data)
    assert result.status_code == 201, result.text
    row = result.json()
    assert row["status"] == "draft" and row["version"] == 1
    assert row["snapshot"]["serving_count"] == ""
    assert row["snapshot"]["operations"][0]["replacement_food_item_id"] is None
    assert db_session.scalar(select(func.count()).select_from(FamilyRecipeVariant)) == 0
    agenda = client.get(f"/api/families/{family.id}/meal-plan", params={"start_date": "2030-01-07", "days": 1}).json()
    assert agenda["days"][0]["slots"][3]["meals"][0]["recipe_id"] == str(base.id)
    listed = client.get(path, params={"base_recipe_id": str(base.id)}).json()
    assert listed[0]["snapshot"] == row["snapshot"]
    # A draft is not a recipe and cannot be applied through the ordinary planner.
    bad = client.patch(f"/api/families/{family.id}/meal-plan/{meal['id']}", json={"recipe_id": row["id"]})
    assert bad.status_code == 422


def test_adaptation_draft_scope_version_and_changed_base(client, db_session, pilot):
    family, other, _, _, base, _, _ = pilot
    meal = _saved_base_meal(client, db_session, pilot)
    data = _incomplete_adaptation_draft(pilot, meal)
    path = f"/api/families/{family.id}/meal-adaptation-drafts"
    row = client.post(path, json=data).json()
    url = f"{path}/{row['id']}"
    updated = client.put(url, json={**data, "expected_version": 1, "name": "Revised draft"})
    assert updated.status_code == 200, updated.text
    assert updated.json()["version"] == 2
    assert client.put(url, json={**data, "expected_version": 1}).status_code == 409
    foreign = f"/api/families/{other.id}/meal-adaptation-drafts"
    assert client.get(foreign, params={"base_recipe_id": str(base.id)}).json() == []
    assert client.post(foreign, json=data).status_code == 404
    assert client.put(f"{foreign}/{row['id']}", json={**data, "expected_version": 2}).status_code == 404
    base.ingredients[0].quantity += Decimal(1)
    db_session.commit()
    listed = client.get(path, params={"base_recipe_id": str(base.id)}).json()
    assert listed[0]["base_changed"] is True


def test_adaptation_draft_rejects_foreign_ingredient_and_duplicate_people(client, db_session, pilot):
    import uuid

    family, _, _, _, _, _, _ = pilot
    meal = _saved_base_meal(client, db_session, pilot)
    data = _incomplete_adaptation_draft(pilot, meal)
    path = f"/api/families/{family.id}/meal-adaptation-drafts"
    assert client.post(path, json={**data, "operations": [{**data["operations"][0], "recipe_ingredient_id": str(uuid.uuid4())}]}).status_code == 422
    assert client.post(path, json={**data, "participants": [data["participants"][0], data["participants"][0]]}).status_code == 422


def test_identified_quantified_variant_with_optional_preparation_can_be_applied(client, pilot):
    family, _, people, _, _, payload, context = pilot
    path = f"/api/families/{family.id}/recipe-variants"
    payload["operations"] = [
        {key: value for key, value in operation.items() if key != "preparation"}
        for operation in payload["operations"]
    ]
    response = client.post(path, json=payload)
    assert response.status_code == 201, response.text
    variant = response.json()
    assert all(operation["preparation"] == "" for operation in variant["operations"])
    checked = client.post(path + f"/{variant['id']}/validate", json=context)
    assert checked.json()["eligible"] is True, checked.text
    active = client.post(path + f"/{variant['id']}/activate", json=context)
    assert active.status_code == 200, active.text
    meal = client.post(f"/api/families/{family.id}/meal-plan", json={
        "date": "2030-01-07", "meal_type": "dinner", "local_time": "19:00",
        "recipe_id": variant["recipe_id"],
        "participants": [{"person_id": str(person.id), "quantity": "1", "unit": "serving"} for person in people],
    })
    assert meal.status_code == 201, meal.text
    assert meal.json()["recipe_id"] == variant["recipe_id"]
    assert len(meal.json()["variant_changes"]) == 2


def test_recipe_edit_inherits_absent_yield_pack_units_and_declared_names(client, db_session, pilot):
    from app.services.recipe_variant_integrity import load_recipe

    family, _, people, _, base, payload, _ = pilot
    base.serving_count = None
    for ingredient in base.ingredients:
        ingredient.unit = "emb"
    db_session.flush()
    meal = _saved_base_meal(client, db_session, pilot)
    operations = [{"recipe_ingredient_id": operation["recipe_ingredient_id"],
                   "replacement_name": name, "quantity": str(index + 1), "unit": "emb"}
                  for index, (operation, name) in enumerate(zip(payload["operations"], ["Natas sem lactose", "Molho caseiro de ervas"], strict=True))]
    response = client.post(f"/api/families/{family.id}/recipe-variants/recipe-edit", json={
        "base_recipe_id": str(base.id), "name": "Receita com trocas aceites", "operations": operations})
    assert response.status_code == 201, response.text
    edit = response.json()
    assert edit["confirmation_mode"] == "recipe_edit"
    assert edit["status"] == "active"
    assert edit["serving_count"] is None
    assert edit["energy_per_serving"] is None
    reviews = client.get(f"/api/families/{family.id}/recipe-adaptations").json()
    assert any(variant["recipe_id"] == edit["recipe_id"] for row in reviews for variant in row["active_variants"])
    recipe = load_recipe(db_session, edit["recipe_id"])
    assert recipe.serving_count is None
    assert all(ingredient.unit == "emb" for ingredient in recipe.ingredients)
    assert all(not ingredient.food_item.compositions for ingredient in recipe.ingredients)
    assert base.ingredients[0].food_item.name == "Massa de trigo"
    saved = client.patch(f"/api/families/{family.id}/meal-plan/{meal['id']}", json={
        "expected_updated_at": meal["updated_at"], "recipe_id": edit["recipe_id"],
        "participants": [{"person_id": str(person.id), "quantity": "1", "unit": "serving"} for person in people]})
    assert saved.status_code == 200, saved.text
    assert len(saved.json()["variant_changes"]) == 2
    assert all(person["energy_kcal"] is None for person in saved.json()["participants"])
    shopping = refresh_shopping_list(db_session, family, start_date=date(2030, 1, 7), days=7)
    automatic = [item for item in shopping.items if item.item_source == "automatic"]
    assert len(automatic) == 2
    assert all(item.unit == "emb" for item in automatic)


def test_recipe_edit_still_rejects_known_restrictions_and_changed_evidence(client, db_session, pilot):
    family, _, people, _, base, payload, _ = pilot
    meal = _saved_base_meal(client, db_session, pilot)
    edit = client.post(f"/api/families/{family.id}/recipe-variants/recipe-edit", json={
        "base_recipe_id": str(base.id), "name": "Only one change", "operations": payload["operations"][:1]}).json()
    assert edit["status"] == "active"
    saved = client.patch(f"/api/families/{family.id}/meal-plan/{meal['id']}", json={
        "recipe_id": edit["recipe_id"], "participants": [{"person_id": str(person.id), "quantity": "1", "unit": "serving"} for person in people]})
    assert saved.status_code == 422, saved.text
    assert "active attendee restrictions" in saved.text
    base.name = "Changed base"
    db_session.commit()
    saved = client.patch(f"/api/families/{family.id}/meal-plan/{meal['id']}", json={"recipe_id": edit["recipe_id"]})
    assert saved.status_code == 422, saved.text
    assert "Base recipe changed" in saved.text



def test_recipe_edit_reuses_identical_family_adaptation_without_new_rows(client, db_session, pilot):
    from sqlalchemy import func, select

    family, _, _, _, base, payload, _ = pilot
    path = f"/api/families/{family.id}/recipe-variants/recipe-edit"
    body = {"base_recipe_id": str(base.id), "name": "Esparguete · família",
            "operations": payload["operations"]}
    first = client.post(path, json=body)
    assert first.status_code == 201, first.text
    original = first.json()
    counts_before = (
        db_session.scalar(select(func.count()).select_from(Recipe)),
        db_session.scalar(select(func.count()).select_from(FoodItem)),
    )
    second = client.post(path, json={**body, "name": "Outra designação · família"})
    assert second.status_code == 201, second.text
    assert second.json()["id"] == original["id"]
    assert second.json()["recipe_id"] == original["recipe_id"]
    assert (
        db_session.scalar(select(func.count()).select_from(Recipe)),
        db_session.scalar(select(func.count()).select_from(FoodItem)),
    ) == counts_before

    edited = [{**operation, "quantity": "121"} if index == 0 else operation
              for index, operation in enumerate(payload["operations"])]
    changed = client.post(path, json={**body, "operations": edited})
    assert changed.status_code == 201, changed.text
    assert changed.json()["recipe_id"] != original["recipe_id"]


def test_recipe_edit_reuses_user_named_replacements_without_duplicate_foods(client, db_session, pilot):
    from sqlalchemy import func, select

    family, _, _, _, base, payload, _ = pilot
    path = f"/api/families/{family.id}/recipe-variants/recipe-edit"
    operations = [{**operation, "replacement_food_item_id": None,
                   "replacement_name": "Natas sem lactose" if index == 0 else "Molho de ervas"}
                  for index, operation in enumerate(payload["operations"])]
    body = {"base_recipe_id": str(base.id), "name": "Receita adaptada · família",
            "operations": operations}
    first = client.post(path, json=body)
    assert first.status_code == 201, first.text
    before = db_session.scalar(select(func.count()).select_from(FoodItem))
    second = client.post(path, json={**body, "name": "Renomeada",
                                     "operations": [{**operation, "replacement_name":
                                         operation["replacement_name"].upper()} for operation in operations]})
    assert second.status_code == 201, second.text
    assert second.json()["recipe_id"] == first.json()["recipe_id"]
    assert db_session.scalar(select(func.count()).select_from(FoodItem)) == before


def test_recipe_edit_scope_invalid_operation_and_missing_description(client, pilot):
    import uuid

    family, other, _, _, base, payload, _ = pilot
    path = f"/api/families/{family.id}/recipe-variants/recipe-edit"
    data = {"base_recipe_id": str(base.id), "name": "Edited", "operations": payload["operations"]}
    assert client.post(f"/api/families/{other.id}/recipe-variants/recipe-edit", json=data).status_code == 404
    assert client.post(path, json={**data, "operations": [{**payload["operations"][0], "recipe_ingredient_id": str(uuid.uuid4())}]}).status_code == 422
    assert client.post(path, json={**data, "operations": [{**payload["operations"][0], "replacement_food_item_id": None}]}).status_code == 422
