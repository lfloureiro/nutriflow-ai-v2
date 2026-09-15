from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.demo_seed import DEMO_PERSON_ID, seed_demo_dataset
from app.development_breakfast_seed import seed_development_breakfast_catalog
from app.development_plan_fit_seed import seed_development_plan_fit
from app.main import app
from app.models.family import Family
from app.models.food_catalog import Recipe, RecipeCompositionSnapshot


def _override_db(db_session: Session):
    def override_get_db():
        yield db_session

    return override_get_db


def test_meal_plan_fit_endpoint_returns_explainable_result(db_session: Session) -> None:
    demo = seed_demo_dataset(
        db_session,
        now=datetime(2026, 9, 15, 12, 0, tzinfo=UTC),
    )
    family = db_session.get(Family, demo.family_id)
    assert family is not None
    seed_development_breakfast_catalog(db_session, families=(family,))
    seed_development_plan_fit(db_session, person_id=DEMO_PERSON_ID)
    db_session.commit()

    recipe = db_session.query(Recipe).filter_by(
        recipe_key="breakfast:recipe:greek-yogurt-muesli-berries"
    ).one()
    composition = db_session.query(RecipeCompositionSnapshot).filter_by(
        recipe_id=recipe.id,
        composition_version="breakfast-estimate-v1",
    ).one()

    app.dependency_overrides[get_db] = _override_db(db_session)
    try:
        with TestClient(app) as client:
            response = client.post(
                f"/api/persons/{DEMO_PERSON_ID}/meal-plan-fit",
                json={
                    "planning_date": demo.planning_date.isoformat(),
                    "meal_type": "breakfast",
                    "daily_nutrition_state_id": str(demo.daily_nutrition_state_id),
                    "candidate": {
                        "candidate_kind": "recipe",
                        "composition_id": str(composition.id),
                        "quantity": "1",
                        "quantity_unit": "serving",
                    },
                },
            )
            assert response.status_code == 200
            payload = response.json()
            assert payload["status"] == "pass"
            assert payload["eligible"] is True
            assert payload["fit_score"] == "1.0000"
            assert payload["candidate"]["name"] == "Iogurte grego, muesli e frutos vermelhos"
            meal_rules = [rule for rule in payload["rule_results"] if rule["scope"] == "meal"]
            assert {rule["target_key"] for rule in meal_rules} == {"protein", "fiber"}
    finally:
        app.dependency_overrides.clear()
