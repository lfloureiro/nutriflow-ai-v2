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
from app.models.food_catalog import Recipe


def _override_db(db_session: Session):
    def override_get_db():
        yield db_session

    return override_get_db


def test_shared_transformation_api_returns_server_classification(db_session: Session) -> None:
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

    app.dependency_overrides[get_db] = _override_db(db_session)
    try:
        with TestClient(app) as client:
            response = client.post(
                f"/api/families/{DEMO_FAMILY_ID}/meal-transformations/proposals",
                json={
                    "planning_date": demo.planning_date.isoformat(),
                    "meal_type": "breakfast",
                    "recipe_id": str(recipe.id),
                    "participants": [
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
                    ],
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    greek = next(
        item
        for item in body["proposals"]
        if item["operation"]["replacement_food_name"] == "Iogurte grego"
    )
    assert greek["kind"] == "plan_adapted"
    assert greek["plan_improvement_participants"] == 1
    assert len(greek["participant_results"]) == 2
    assert {
        item["after_fit"]["nutrition_plan_authority"]["state"]
        for item in greek["participant_results"]
    } == {"partial_plan_coverage", "no_active_plan"}
