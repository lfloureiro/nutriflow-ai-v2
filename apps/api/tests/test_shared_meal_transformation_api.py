from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.demo_seed import DEMO_FAMILY_ID, DEMO_MARTA_ID, DEMO_PERSON_ID, seed_demo_dataset
from app.development_breakfast_seed import seed_development_breakfast_catalog
from app.development_plan_fit_seed import seed_development_plan_fit
from app.development_transformation_seed import seed_development_transformations
from app.main import app
from app.models.daily_nutrition_state import DailyNutritionState
from app.models.family import Family
from app.models.food_adverse_reaction import FoodAdverseReaction
from app.models.food_catalog import Recipe
from app.models.meal import MealEvent


def _override_db(db_session: Session):
    def override_get_db():
        yield db_session

    return override_get_db


def _seed(db_session: Session):
    demo = seed_demo_dataset(
        db_session,
        now=datetime(2026, 9, 15, 12, 0, tzinfo=UTC),
    )
    family = db_session.get(Family, demo.family_id)
    assert family is not None
    seed_development_breakfast_catalog(db_session, families=(family,))
    seed_development_transformations(db_session, families=(family,))
    seed_development_plan_fit(db_session, person_id=DEMO_PERSON_ID)
    db_session.commit()

    recipe = db_session.scalar(
        select(Recipe).where(
            Recipe.recipe_key == "breakfast:recipe:yogurt-muesli-banana"
        )
    )
    assert recipe is not None
    states = {
        state.person_id: state
        for state in db_session.scalars(
            select(DailyNutritionState).where(
                DailyNutritionState.person_id.in_((DEMO_PERSON_ID, DEMO_MARTA_ID)),
                DailyNutritionState.state_date == demo.planning_date,
            )
        ).all()
    }
    assert states[DEMO_PERSON_ID].id is not None
    assert states[DEMO_MARTA_ID].id is not None
    participants = [
        {
            "person_id": str(DEMO_PERSON_ID),
            "daily_nutrition_state_id": str(states[DEMO_PERSON_ID].id),
            "quantity": "1",
            "quantity_unit": "serving",
        },
        {
            "person_id": str(DEMO_MARTA_ID),
            "daily_nutrition_state_id": str(states[DEMO_MARTA_ID].id),
            "quantity": "1",
            "quantity_unit": "serving",
        },
    ]
    return demo, recipe, participants


def _preview_payload(demo, recipe: Recipe, participants):
    return {
        "planning_date": demo.planning_date.isoformat(),
        "meal_type": "breakfast",
        "recipe_id": str(recipe.id),
        "participants": participants,
    }


def _greek_proposal(body):
    return next(
        item
        for item in body["proposals"]
        if item["operation"]["replacement_food_name"] == "Iogurte grego"
    )


def _cancel_seed_breakfast(db_session: Session) -> None:
    event = db_session.scalar(
        select(MealEvent).where(
            MealEvent.family_id == DEMO_FAMILY_ID,
            MealEvent.meal_type == "breakfast",
        )
    )
    assert event is not None
    event.status = "cancelled"
    db_session.commit()


def test_shared_transformation_api_returns_server_classification(db_session: Session) -> None:
    demo, recipe, participants = _seed(db_session)

    app.dependency_overrides[get_db] = _override_db(db_session)
    try:
        with TestClient(app) as client:
            response = client.post(
                f"/api/families/{DEMO_FAMILY_ID}/meal-transformations/proposals",
                json=_preview_payload(demo, recipe, participants),
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    greek = _greek_proposal(response.json())
    assert greek["kind"] == "plan_adapted"
    assert greek["plan_improvement_participants"] == 1
    assert len(greek["participant_results"]) == 2
    assert {
        item["after_fit"]["nutrition_plan_authority"]["state"]
        for item in greek["participant_results"]
    } == {"partial_plan_coverage", "no_active_plan"}


def test_shared_transformation_plan_materializes_selected_server_proposal(
    db_session: Session,
) -> None:
    demo, recipe, participants = _seed(db_session)
    _cancel_seed_breakfast(db_session)

    app.dependency_overrides[get_db] = _override_db(db_session)
    try:
        with TestClient(app) as client:
            preview = client.post(
                f"/api/families/{DEMO_FAMILY_ID}/meal-transformations/proposals",
                json=_preview_payload(demo, recipe, participants),
            )
            assert preview.status_code == 200
            greek = _greek_proposal(preview.json())
            operation = greek["operation"]
            response = client.post(
                f"/api/families/{DEMO_FAMILY_ID}/meal-transformations/plan",
                json={
                    **_preview_payload(demo, recipe, participants),
                    "recipe_ingredient_id": operation["recipe_ingredient_id"],
                    "replacement_food_item_id": operation["replacement_food_item_id"],
                    "scheduled_at": "2026-09-15T08:30:00Z",
                    "title": "Pequeno-almoço adaptado",
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "planned"
    assert body["transformation_kind"] == "plan_adapted"
    assert body["recipe_id"] == str(recipe.id)
    assert set(body["person_ids"]) == {str(DEMO_PERSON_ID), str(DEMO_MARTA_ID)}
    assert len(body["serving_ids"]) == 2


def test_shared_transformation_plan_revalidates_safety_after_preview(
    db_session: Session,
) -> None:
    demo, recipe, participants = _seed(db_session)
    _cancel_seed_breakfast(db_session)

    app.dependency_overrides[get_db] = _override_db(db_session)
    try:
        with TestClient(app) as client:
            preview = client.post(
                f"/api/families/{DEMO_FAMILY_ID}/meal-transformations/proposals",
                json=_preview_payload(demo, recipe, participants),
            )
            assert preview.status_code == 200
            operation = _greek_proposal(preview.json())["operation"]

            db_session.add(
                FoodAdverseReaction(
                    person_id=DEMO_MARTA_ID,
                    reaction_type="intolerance",
                    subject_type="ingredient",
                    subject_key="breakfast:ingredient:greek-yogurt",
                    severity="high",
                    is_mandatory=True,
                    source="user",
                    start_date=demo.planning_date,
                )
            )
            db_session.commit()

            response = client.post(
                f"/api/families/{DEMO_FAMILY_ID}/meal-transformations/plan",
                json={
                    **_preview_payload(demo, recipe, participants),
                    "recipe_ingredient_id": operation["recipe_ingredient_id"],
                    "replacement_food_item_id": operation["replacement_food_item_id"],
                    "scheduled_at": "2026-09-15T08:30:00Z",
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    assert "no longer available or safe" in response.json()["detail"]


def test_shared_transformation_plan_returns_conflict_for_occupied_slot(
    db_session: Session,
) -> None:
    demo, recipe, participants = _seed(db_session)

    app.dependency_overrides[get_db] = _override_db(db_session)
    try:
        with TestClient(app) as client:
            preview = client.post(
                f"/api/families/{DEMO_FAMILY_ID}/meal-transformations/proposals",
                json=_preview_payload(demo, recipe, participants),
            )
            assert preview.status_code == 200
            operation = _greek_proposal(preview.json())["operation"]
            response = client.post(
                f"/api/families/{DEMO_FAMILY_ID}/meal-transformations/plan",
                json={
                    **_preview_payload(demo, recipe, participants),
                    "recipe_ingredient_id": operation["recipe_ingredient_id"],
                    "replacement_food_item_id": operation["replacement_food_item_id"],
                    "scheduled_at": "2026-09-15T08:30:00Z",
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 409
    assert "already planned" in response.json()["detail"]
