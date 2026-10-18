import uuid
from datetime import UTC, date, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.db.session import get_db
from app.fodmap_guidance_seed import import_public_guidance
from app.main import app
from app.models import Family, FoodItem, MealEvent, Person, RecipeIngredient
from app.models.dietary_review import PersonHealthCondition
from app.models.nutrition_constraint import NutritionConstraint
from app.models.nutrition_plan import NutritionPlan, NutritionPlanRule
from app.models.planning_workspace import FamilyWeekSetup, RetailAlternative
from app.retail_alternatives_seed import ROWS, import_retail_observations
from tests.test_weekly_planning_api import _setup, _slot


@pytest.fixture
def client(db_session):
    def override():
        yield db_session

    app.dependency_overrides[get_db] = override
    try:
        with TestClient(app) as value:
            yield value
    finally:
        app.dependency_overrides.clear()


def _family(db):
    family = Family(name="Workspace family")
    other = Family(name="Private family")
    db.add_all([family, other])
    db.flush()
    people = [Person(family_id=family.id, first_name=name) for name in ("Ana", "Bruno")]
    food = FoodItem(catalog_key="legacy-v1:ingredient:54", name="Esparguete")
    hidden = FoodItem(family_id=other.id, catalog_key="private:food", name="Private ingredient")
    db.add_all([*people, food, hidden])
    db.flush()
    return family, other, people, food, hidden


def test_automatic_sibo_defaults_respect_attendance_status_dates_and_family(client, db_session):
    family, other, people, food, _ = _family(db_session)
    import_public_guidance(db_session, family.id)
    condition = PersonHealthCondition(
        person_id=people[0].id,
        code="sibo",
        name="SIBO",
        status="reported",
        source="user",
        started_on=date(2026, 10, 20),
        ended_on=date(2026, 10, 21),
    )
    db_session.add(condition)
    db_session.flush()
    path = f"/api/families/{family.id}/planning-restrictions"
    payload = {
        "person_ids": [str(p.id) for p in people],
        "week_start": "2026-10-19",
        "meal_types": ["dinner"],
    }
    result = client.post(path, json=payload)
    assert result.status_code == 200
    assert result.json()["excluded_food_item_ids"] == [str(food.id)]
    assert result.json()["sources"][0]["dates"] == ["2026-10-20", "2026-10-21"]
    assert (
        client.post(path, json={**payload, "person_ids": [str(people[1].id)]}).json()["sources"]
        == []
    )
    assert (
        client.post(f"/api/families/{other.id}/planning-restrictions", json=payload).status_code
        == 404
    )
    for status in ("resolved", "suspected"):
        condition.status = status
        db_session.flush()
        assert client.post(path, json=payload).json()["excluded_food_item_ids"] == []
    condition.status = "confirmed"
    condition.code = "unconfigured"
    db_session.flush()
    result = client.post(path, json=payload).json()
    assert result["sources"] == [] and result["warnings"]


def test_automatic_diet_defaults_use_effective_plan_and_meal_scope(client, db_session):
    family, _, people, food, _ = _family(db_session)
    constraint = NutritionConstraint(
        person_id=people[0].id,
        constraint_type="exclusion",
        target_type="food_item",
        target_key=food.catalog_key,
        operator="exclude",
        is_mandatory=True,
        source="user",
    )
    plan = NutritionPlan(
        person_id=people[0].id,
        title="Dieta ativa",
        status="active",
        source_type="user",
        valid_from=date(2026, 10, 20),
        valid_until=date(2026, 10, 21),
    )
    db_session.add_all([constraint, plan])
    db_session.flush()
    db_session.add(
        NutritionPlanRule(
            nutrition_plan_id=plan.id,
            rule_kind="constraint",
            nutrition_constraint_id=constraint.id,
            meal_type="lunch",
            applies_outside_plan=False,
        )
    )
    db_session.flush()
    path = f"/api/families/{family.id}/planning-restrictions"
    payload = {
        "person_ids": [str(p.id) for p in people],
        "week_start": "2026-10-19",
        "meal_types": ["dinner"],
    }
    assert client.post(path, json=payload).json()["sources"] == []
    result = client.post(path, json={**payload, "meal_types": ["lunch"]}).json()
    assert result["excluded_food_item_ids"] == [str(food.id)]
    assert result["sources"][0]["dates"] == ["2026-10-20", "2026-10-21"]
    plan.status = "inactive"
    db_session.flush()
    assert client.post(path, json={**payload, "meal_types": ["lunch"]}).json()["sources"] == []


def test_condition_defaults_cannot_be_bypassed_on_weekly_preview_or_accept(client, db_session):
    family, ana, bruno, recipe, composition = _setup(db_session, "automatic-sibo")
    food = FoodItem(catalog_key="legacy-v1:ingredient:54", name="Esparguete")
    db_session.add(food)
    db_session.flush()
    db_session.add(
        RecipeIngredient(
            recipe_id=recipe.id, food_item_id=food.id, quantity=100, unit="g", sort_order=0
        )
    )
    db_session.flush()
    import_public_guidance(db_session, family.id)
    payload = {
        "person_ids": [str(ana.id), str(bruno.id)],
        "slots": [
            _slot(
                "dinner",
                scheduled_at=datetime(2026, 9, 17, 19, tzinfo=UTC),
                meal_type="dinner",
                composition=composition,
            )
        ],
        "max_combinations": 10,
    }
    path = f"/api/families/{family.id}/weekly-planning"
    assert client.post(path + "/proposals", json=payload).json()["selected_plan"] is not None
    db_session.add(
        PersonHealthCondition(
            person_id=ana.id, code="sibo", name="SIBO", status="reported", source="user"
        )
    )
    db_session.flush()
    assert client.post(path + "/proposals", json=payload).json()["selected_plan"] is None
    accepted = client.post(
        path + "/plan",
        json={
            **payload,
            "expected_choices": [{"slot_key": "dinner", "candidate_key": recipe.recipe_key}],
        },
    )
    assert accepted.status_code == 409
    assert db_session.scalar(select(func.count()).select_from(MealEvent)) == 0
    assert db_session.get(RecipeIngredient, recipe.ingredients[0].id).food_item_id == food.id


def test_week_setup_persists_scoped_choices_with_conflict_detection(client, db_session):
    family, other, people, food, _ = _family(db_session)
    path = f"/api/families/{family.id}/planning-setup/2026-10-19"
    assert client.get(path).json() is None
    payload = {
        "person_ids": [str(p.id) for p in people],
        "meal_types": ["dinner"],
        "excluded_food_item_ids": [str(food.id)],
        "expected_version": 0,
    }
    response = client.put(path, json=payload)
    assert response.status_code == 200
    assert response.json()["version"] == 1
    assert client.get(path).json()["excluded_food_item_ids"] == [str(food.id)]
    assert client.put(path, json=payload).status_code == 409
    assert (
        client.put(
            path, json={**payload, "expected_version": 1, "meal_types": ["lunch", "dinner"]}
        ).json()["version"]
        == 2
    )
    assert client.get(f"/api/families/{other.id}/planning-setup/2026-10-19").json() is None
    assert db_session.scalar(select(func.count()).select_from(FamilyWeekSetup)) == 1


def test_week_setup_rejects_invalid_context_and_foreign_data(client, db_session):
    family, other, people, food, hidden = _family(db_session)
    outsider = Person(family_id=other.id, first_name="Outsider")
    db_session.add(outsider)
    db_session.flush()
    path = f"/api/families/{family.id}/planning-setup/2026-10-19"
    payload = {"person_ids": [str(p.id) for p in people], "meal_types": ["dinner"]}
    assert client.put(path.replace("/2026-10-19", "/2026-10-20"), json=payload).status_code == 422
    assert (
        client.put(
            path, json={**payload, "person_ids": [str(people[0].id), str(outsider.id)]}
        ).status_code
        == 404
    )
    for ids in [[str(hidden.id)], [str(food.id), str(food.id)], [str(uuid.uuid4())]]:
        assert client.put(path, json={**payload, "excluded_food_item_ids": ids}).status_code == 422
    assert client.put(path, json={**payload, "meal_types": []}).status_code == 422


def test_retail_observations_are_idempotent_and_do_not_claim_product_tolerance(client, db_session):
    family, _, _, food, hidden = _family(db_session)
    assert import_retail_observations(db_session) == len(ROWS)
    assert import_retail_observations(db_session) == 0
    products = client.get(f"/api/families/{family.id}/retail-alternatives").json()
    assert len(products) == len(ROWS)
    pasta = [p for p in products if p["alternative_group"] == "rice-corn-pasta"]
    assert len(pasta) == 2
    assert all(str(food.id) in p["applicable_food_item_ids"] for p in pasta)
    assert all(str(hidden.id) not in p["applicable_food_item_ids"] for p in products)
    assert all(p["observed_on"] == "2026-10-18" for p in products)
    assert any(p["nutrition_per_100"] is None for p in pasta)
    assert {p["evidence_level"] for p in pasta} == {
        "retailer_description_only",
        "retailer_ingredients_and_nutrition",
    }
    assert not any("fodmap_certified" in p for p in products)
    assert db_session.scalar(select(func.count()).select_from(RetailAlternative)) == len(ROWS)
    assert db_session.scalar(select(func.count()).select_from(MealEvent)) == 0


def test_explicit_weekly_exclusion_is_a_server_gate_and_revalidated_on_apply(client, db_session):
    family, ana, bruno, recipe, composition = _setup(db_session, "workspace-exclusions")
    food = FoodItem(catalog_key="test:garlic", name="Alho")
    db_session.add(food)
    db_session.flush()
    db_session.add(
        RecipeIngredient(
            recipe_id=recipe.id, food_item_id=food.id, quantity=10, unit="g", sort_order=0
        )
    )
    db_session.flush()
    payload = {
        "person_ids": [str(ana.id), str(bruno.id)],
        "slots": [
            _slot(
                "dinner",
                scheduled_at=datetime(2026, 9, 17, 19, tzinfo=UTC),
                meal_type="dinner",
                composition=composition,
            )
        ],
        "max_combinations": 10,
    }
    path = f"/api/families/{family.id}/weekly-planning"
    original = client.post(path + "/proposals", json=payload)
    assert original.status_code == 201
    assert original.json()["selected_plan"] is not None
    blocked = client.post(
        path + "/proposals", json={**payload, "excluded_food_item_ids": [str(food.id)]}
    )
    assert blocked.status_code == 201
    assert blocked.json()["selected_plan"] is None
    assert any(
        "requested_exclusions" in r for r in blocked.json()["skipped_slots"][0]["exclusion_reasons"]
    )
    apply_payload = {
        **payload,
        "excluded_food_item_ids": [str(food.id)],
        "expected_choices": [{"slot_key": "dinner", "candidate_key": recipe.recipe_key}],
    }
    assert client.post(path + "/plan", json=apply_payload).status_code == 409
    assert db_session.scalar(select(func.count()).select_from(MealEvent)) == 0


def test_missing_recipe_ingredients_do_not_pass_requested_exclusions(client, db_session):
    family, ana, bruno, _, composition = _setup(db_session, "workspace-missing")
    food = FoodItem(catalog_key="test:onion", name="Cebola")
    db_session.add(food)
    db_session.flush()
    payload = {
        "person_ids": [str(ana.id), str(bruno.id)],
        "excluded_food_item_ids": [str(food.id)],
        "slots": [
            _slot(
                "dinner",
                scheduled_at=datetime(2026, 9, 17, 19, tzinfo=UTC),
                meal_type="dinner",
                composition=composition,
            )
        ],
    }
    response = client.post(f"/api/families/{family.id}/weekly-planning/proposals", json=payload)
    assert response.status_code == 201
    assert response.json()["selected_plan"] is None
    assert any(
        "ingredient_evidence_missing" in reason
        for reason in response.json()["skipped_slots"][0]["exclusion_reasons"]
    )


def test_unknown_exclusion_id_cannot_be_silently_ignored(client, db_session):
    family, ana, bruno, _, composition = _setup(db_session, "workspace-invalid-food")
    payload = {
        "person_ids": [str(ana.id), str(bruno.id)],
        "excluded_food_item_ids": [str(uuid.uuid4())],
        "slots": [
            _slot(
                "dinner",
                scheduled_at=datetime(2026, 9, 17, 19, tzinfo=UTC),
                meal_type="dinner",
                composition=composition,
            )
        ],
    }
    assert (
        client.post(
            f"/api/families/{family.id}/weekly-planning/proposals", json=payload
        ).status_code
        == 422
    )


def test_attendance_persists_and_rejects_invalid_slots(client, db_session):
    family, _, people, _, _ = _family(db_session)
    path = f"/api/families/{family.id}/planning-setup/2026-10-19"
    entry = {"planning_date": "2026-10-20", "meal_type": "dinner", "person_ids": []}
    payload = {
        "person_ids": [str(p.id) for p in people],
        "meal_types": ["dinner"],
        "attendance": [entry],
    }
    assert client.put(path, json=payload).status_code == 200
    assert client.get(path).json()["attendance"] == [entry]
    for attendance in [
        [entry, entry],
        [{**entry, "planning_date": "2026-10-26"}],
        [{**entry, "meal_type": "lunch"}],
        [{**entry, "person_ids": [str(uuid.uuid4()), str(uuid.uuid4())]}],
        [{**entry, "person_ids": [str(people[0].id)]}],
    ]:
        assert (
            client.put(
                path, json={**payload, "expected_version": 1, "attendance": attendance}
            ).status_code
            == 422
        )


def test_restriction_preview_ignores_a_person_absent_all_week(client, db_session):
    family, _, people, food, _ = _family(db_session)
    import_public_guidance(db_session, family.id)
    db_session.add(
        PersonHealthCondition(
            person_id=people[0].id, code="sibo", name="SIBO", status="reported", source="user"
        )
    )
    db_session.flush()
    payload = {
        "person_ids": [str(p.id) for p in people],
        "week_start": "2026-10-19",
        "meal_types": ["dinner"],
    }
    path = f"/api/families/{family.id}/planning-restrictions"
    assert str(food.id) in client.post(path, json=payload).json()["excluded_food_item_ids"]
    from datetime import timedelta

    payload["attendance"] = [
        {
            "planning_date": (date(2026, 10, 19) + timedelta(days=i)).isoformat(),
            "meal_type": "dinner",
            "person_ids": [],
        }
        for i in range(7)
    ]
    assert client.post(path, json=payload).json()["sources"] == []


def test_sibo_applies_only_to_actual_slot_attendees_and_acceptance(client, db_session):
    from decimal import Decimal

    from app.models.daily_nutrition_state import DailyNutritionState
    from app.models.meal import MealParticipant, Serving
    from tests.test_weekly_planning_api import LUNCH_AT, PLANNING_DATE

    family, ana, bruno, recipe, composition = _setup(db_session, "attendance-sibo")
    carla = Person(family_id=family.id, first_name="Carla")
    food = FoodItem(catalog_key="legacy-v1:ingredient:54", name="Esparguete")
    db_session.add_all([carla, food])
    db_session.flush()
    db_session.add_all(
        [
            DailyNutritionState(
                person_id=carla.id,
                state_date=PLANNING_DATE,
                timezone="Europe/Lisbon",
                energy_consumed_kcal=Decimal(1000),
                energy_planned_kcal=Decimal(0),
                energy_remaining_min_kcal=Decimal(400),
                energy_remaining_max_kcal=Decimal(800),
                calculation_version="test-attendance",
                computed_at=LUNCH_AT,
            ),
            RecipeIngredient(
                recipe_id=recipe.id, food_item_id=food.id, quantity=100, unit="g", sort_order=0
            ),
            PersonHealthCondition(
                person_id=ana.id, code="sibo", name="SIBO", status="reported", source="user"
            ),
        ]
    )
    db_session.flush()
    import_public_guidance(db_session, family.id)
    slot = _slot(
        "dinner",
        scheduled_at=datetime(2026, 9, 17, 19, tzinfo=UTC),
        meal_type="dinner",
        composition=composition,
    )
    slot["person_ids"] = [str(ana.id), str(bruno.id)]
    payload = {
        "person_ids": [str(p.id) for p in (ana, bruno, carla)],
        "slots": [slot],
        "max_combinations": 10,
    }
    path = f"/api/families/{family.id}/weekly-planning"
    assert client.post(path + "/proposals", json=payload).json()["selected_plan"] is None
    slot["person_ids"] = [str(bruno.id), str(carla.id)]
    preview = client.post(path + "/proposals", json=payload)
    assert preview.status_code == 201, preview.text
    assert preview.json()["selected_plan"] is not None, preview.text
    response = client.post(
        path + "/plan",
        json={
            **payload,
            "expected_choices": [{"slot_key": "dinner", "candidate_key": recipe.recipe_key}],
        },
    )
    assert response.status_code == 201, response.text
    assert set(db_session.scalars(select(MealParticipant.person_id).join(Serving))) == {
        bruno.id,
        carla.id,
    }


def test_week_setup_persists_meal_sources_and_rejects_unknown_modes(client, db_session):
    family, _, people, _, _ = _family(db_session)
    path = f"/api/families/{family.id}/planning-setup/2026-10-19"
    payload = {
        "person_ids": [str(p.id) for p in people],
        "meal_types": ["lunch", "dinner"],
        "meal_sources": {"lunch": "delivery", "dinner": "home"},
    }
    response = client.put(path, json=payload)
    assert response.status_code == 200, response.text
    assert client.get(path).json()["meal_sources"] == payload["meal_sources"]
    assert (
        client.put(
            path, json={**payload, "expected_version": 1, "meal_sources": {"lunch": "unknown"}}
        ).status_code
        == 422
    )
    assert (
        client.put(
            path, json={**payload, "expected_version": 1, "meal_sources": {"midnight": "home"}}
        ).status_code
        == 422
    )


def test_expanded_retail_evidence_preserves_unknown_nutrition_and_known_allergens(
    client, db_session
):
    family, _, _, _, _ = _family(db_session)
    flour = FoodItem(catalog_key="legacy-v1:ingredient:58", name="Farinha de trigo")
    db_session.add(flour)
    db_session.flush()
    import_retail_observations(db_session)
    products = client.get(f"/api/families/{family.id}/retail-alternatives").json()
    thickeners = [p for p in products if p["alternative_group"] == "rice-corn-thickener"]
    assert len(thickeners) == 4
    assert all(p["applicable_food_item_ids"] == [str(flour.id)] for p in thickeners)
    rice = next(p for p in products if "3452448.html" in p["product_url"])
    assert rice["nutrition_per_100"] is None
    assert rice["evidence_level"] == "retailer_ingredients_only"
    assert "ovo" in rice["ingredient_summary"]
    chives = next(p for p in products if p["alternative_group"] == "chives-seasoning")
    assert "mostarda" in chives["ingredient_summary"]
    yogurt = next(p for p in products if "3921275.html" in p["product_url"])
    assert yogurt["nutrition_per_100"]["energy_kcal"] == "38"
    assert "leite" in yogurt["ingredient_summary"].lower()
