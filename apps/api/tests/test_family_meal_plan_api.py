import uuid
from datetime import UTC, datetime
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.development_breakfast_seed import seed_development_breakfast_catalog
from app.main import app
from app.models.family import Family
from app.models.food_catalog import FoodCompositionSnapshot, FoodItem, Recipe
from app.models.meal import MealEvent, MealParticipant, Serving
from app.models.meal_transformation_application import MealTransformationApplication
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
            reference_quantity=Decimal(100),
            reference_unit="g",
            energy_kcal=Decimal(100),
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
            "ingredients": [{"food_item_id": str(ingredient.id), "quantity": "1000", "unit": "g"}],
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
        Decimal(300),
        Decimal(500),
    ]

    duplicate = _request(
        db_session,
        "POST",
        f"/api/families/{family.id}/meal-plan",
        json={
            "date": PLAN_DATE,
            "meal_type": "dinner",
            "local_time": "21:00",
            "recipe_id": recipe_id,
            "participants": [{"person_id": str(ana.id), "quantity": "300", "unit": "g"}],
        },
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["detail"] == (
        "A meal is already planned for this meal slot on this date."
    )

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
    assert Decimal(updated.json()["participants"][0]["energy_kcal"]) == Decimal(400)

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


def test_family_meal_plan_accepts_shared_breakfast_and_enforces_slot(
    db_session: Session,
) -> None:
    family = Family(name="Shared breakfast planner", timezone="Europe/Lisbon")
    person = Person(family=family, first_name="Ana", timezone="Europe/Lisbon")
    db_session.add(family)
    db_session.flush()
    seed_development_breakfast_catalog(db_session)
    db_session.flush()

    recipes = list(
        db_session.scalars(
            select(Recipe)
            .where(Recipe.source == "development-breakfast")
            .order_by(Recipe.recipe_key)
            .limit(2)
        ).all()
    )
    assert len(recipes) == 2

    created = _request(
        db_session,
        "POST",
        f"/api/families/{family.id}/meal-plan",
        json={
            "date": PLAN_DATE,
            "meal_type": "breakfast",
            "local_time": "08:30",
            "recipe_id": str(recipes[0].id),
            "participants": [{"person_id": str(person.id)}],
        },
    )
    assert created.status_code == 201
    entry = created.json()
    assert entry["recipe_id"] == str(recipes[0].id)
    assert entry["meal_type"] == "breakfast"

    updated = _request(
        db_session,
        "PATCH",
        f"/api/families/{family.id}/meal-plan/{entry['id']}",
        json={"recipe_id": str(recipes[1].id)},
    )
    assert updated.status_code == 200
    assert updated.json()["recipe_id"] == str(recipes[1].id)

    wrong_slot = _request(
        db_session,
        "POST",
        f"/api/families/{family.id}/meal-plan",
        json={
            "date": PLAN_DATE,
            "meal_type": "lunch",
            "local_time": "13:00",
            "recipe_id": str(recipes[0].id),
            "participants": [{"person_id": str(person.id)}],
        },
    )
    assert wrong_slot.status_code == 422
    assert "not suitable for meal type 'lunch'" in wrong_slot.json()["detail"]

    wrong_update = _request(
        db_session,
        "PATCH",
        f"/api/families/{family.id}/meal-plan/{entry['id']}",
        json={"meal_type": "lunch"},
    )
    assert wrong_update.status_code == 422
    assert "not suitable for meal type 'lunch'" in wrong_update.json()["detail"]


def test_transformed_meal_is_visible_but_read_only_in_standard_planner(
    db_session: Session,
) -> None:
    family = Family(name="Transformed planner", timezone="Europe/Lisbon")
    ana = Person(family=family, first_name="Ana", timezone="Europe/Lisbon")
    db_session.add(family)
    db_session.flush()
    recipe_id = _recipe(db_session, family)
    recipe = db_session.get(Recipe, uuid.UUID(recipe_id))
    assert recipe is not None
    assert recipe.ingredients
    assert recipe.compositions

    source_ingredient = recipe.ingredients[0]
    source_food_item = source_ingredient.food_item
    replacement = FoodItem(
        family=family,
        catalog_key=f"test:replacement:{uuid.uuid4()}",
        name="Ingrediente alternativo",
        food_kind="ingredient",
        source="test",
        is_active=True,
    )
    db_session.add(replacement)
    db_session.flush()

    event = MealEvent(
        family=family,
        meal_type="dinner",
        title=recipe.name,
        scheduled_at=datetime(2026, 8, 23, 19, 0, tzinfo=UTC),
        timezone=family.timezone,
        status="planned",
        source="recommendation",
        source_reference="meal-transformation:test",
    )
    participant = MealParticipant(
        meal_event=event,
        person=ana,
        status="planned",
    )
    Serving(
        meal_participant=participant,
        recipe=recipe,
        item_type="recipe",
        item_key=recipe.recipe_key,
        item_name=recipe.name,
        status="planned",
        quantity_planned=Decimal(250),
        quantity_unit="g",
        energy_planned_kcal=Decimal(275),
        nutrition_source="transformed",
        source_reference="meal-transformation:test",
    )
    application = MealTransformationApplication(
        meal_event=event,
        recipe=recipe,
        source_recipe_composition_snapshot=recipe.compositions[-1],
        recipe_ingredient=source_ingredient,
        source_food_item=source_food_item,
        replacement_food_item=replacement,
        sort_order=0,
        operation_type="replace_ingredient",
        transformation_kind="plan_adapted",
        substitution_group="test-group",
        source_food_name=source_food_item.name,
        source_quantity=source_ingredient.quantity,
        source_unit=source_ingredient.unit,
        replacement_food_name=replacement.name,
        replacement_quantity=source_ingredient.quantity,
        replacement_unit=source_ingredient.unit,
        engine_version="test-transformation-v1",
        evidence={"classification": "plan_adapted"},
    )
    db_session.add_all([event, application])
    db_session.commit()

    plan = _request(
        db_session,
        "GET",
        f"/api/families/{family.id}/meal-plan",
        params={"start_date": PLAN_DATE, "days": 1},
    )
    assert plan.status_code == 200
    dinner = plan.json()["days"][0]["slots"][3]["meals"][0]
    assert dinner["id"] == str(event.id)
    assert dinner["recipe_name"] == recipe.name
    assert dinner["transformations"] == [
        {
            "id": str(application.id),
            "transformation_kind": "plan_adapted",
            "operation_type": "replace_ingredient",
            "source_food_name": source_food_item.name,
            "replacement_food_name": replacement.name,
        }
    ]

    update = _request(
        db_session,
        "PATCH",
        f"/api/families/{family.id}/meal-plan/{event.id}",
        json={"location": "Outro local"},
    )
    assert update.status_code == 409
    assert "read-only" in update.json()["detail"]

    removed = _request(
        db_session,
        "DELETE",
        f"/api/families/{family.id}/meal-plan/{event.id}",
    )
    assert removed.status_code == 204


def _sibo_manual_context(db_session):
    from datetime import date

    from app.fodmap_guidance_seed import import_public_guidance
    from app.models.dietary_review import PersonHealthCondition

    family = Family(name="Manual restrictions", timezone="Europe/Lisbon")
    ana = Person(family=family, first_name="Ana")
    rui = Person(family=family, first_name="Rui")
    db_session.add(family)
    db_session.flush()
    recipe_id = _recipe(db_session, family)
    food = db_session.get(Recipe, uuid.UUID(recipe_id)).ingredients[0].food_item
    food.catalog_key = "legacy-v1:ingredient:29"
    food.name = "Cebola"
    db_session.add(
        PersonHealthCondition(
            person_id=ana.id,
            code="sibo",
            name="SIBO",
            status="reported",
            source="user",
            started_on=date(2026, 8, 24),
        )
    )
    db_session.flush()
    import_public_guidance(db_session, family.id)
    return family, ana, rui, recipe_id


def test_manual_plan_revalidates_changed_date_and_attendees_without_partial_writes(db_session):
    family, ana, rui, recipe_id = _sibo_manual_context(db_session)
    path = f"/api/families/{family.id}/meal-plan"
    before = _request(
        db_session,
        "POST",
        path,
        json={
            "date": "2026-08-23",
            "meal_type": "dinner",
            "local_time": "20:00",
            "recipe_id": recipe_id,
            "participants": [{"person_id": str(ana.id)}],
        },
    )
    assert before.status_code == 201, before.text
    changed = _request(
        db_session, "PATCH", path + "/" + before.json()["id"], json={"date": "2026-08-25"}
    )
    assert changed.status_code == 422, changed.text
    assert "Cebola" in changed.json()["detail"]
    original = db_session.get(MealEvent, uuid.UUID(before.json()["id"]))
    assert original.scheduled_at.date().isoformat() == "2026-08-23"
    # A restriction belonging to an absent person must not block the original dish.
    allowed = _request(
        db_session,
        "POST",
        path,
        json={
            "date": "2026-08-25",
            "meal_type": "dinner",
            "local_time": "20:00",
            "recipe_id": recipe_id,
            "participants": [{"person_id": str(rui.id)}],
        },
    )
    assert allowed.status_code == 201, allowed.text
    changed = _request(
        db_session,
        "PATCH",
        path + "/" + allowed.json()["id"],
        json={
            "participants": [{"person_id": str(rui.id)}, {"person_id": str(ana.id)}],
            "notes": "must not persist",
        },
    )
    assert changed.status_code == 422, changed.text
    event = db_session.get(MealEvent, uuid.UUID(allowed.json()["id"]))
    assert {p.person_id for p in event.participants} == {rui.id}
    assert event.notes is None


def test_manual_plan_rejects_base_with_active_restriction_before_saving(db_session):
    family, ana, _, recipe_id = _sibo_manual_context(db_session)
    response = _request(
        db_session,
        "POST",
        f"/api/families/{family.id}/meal-plan",
        json={
            "date": "2026-08-25",
            "meal_type": "dinner",
            "local_time": "20:00",
            "recipe_id": recipe_id,
            "participants": [{"person_id": str(ana.id)}],
        },
    )
    assert response.status_code == 422, response.text
    assert "Cebola" in response.json()["detail"]
    assert list(db_session.scalars(select(MealEvent))) == []
    assert list(db_session.scalars(select(Serving))) == []


def test_manual_plan_checks_restrictions_beyond_first_twenty_attendees(db_session):
    family, ana, _, recipe_id = _sibo_manual_context(db_session)
    guests = [Person(family_id=family.id, first_name=f"Guest {number}") for number in range(20)]
    db_session.add_all(guests)
    db_session.commit()
    response = _request(
        db_session,
        "POST",
        f"/api/families/{family.id}/meal-plan",
        json={
            "date": "2026-08-25",
            "meal_type": "dinner",
            "local_time": "20:00",
            "recipe_id": recipe_id,
            "participants": [{"person_id": str(p.id)} for p in [*guests, ana]],
        },
    )
    assert response.status_code == 422, response.text
    assert "Cebola" in response.json()["detail"]
    assert list(db_session.scalars(select(MealEvent))) == []
