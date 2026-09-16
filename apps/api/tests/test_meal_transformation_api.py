from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.demo_seed import DEMO_PERSON_ID, seed_demo_dataset
from app.development_breakfast_seed import seed_development_breakfast_catalog
from app.development_plan_fit_seed import seed_development_plan_fit
from app.development_transformation_seed import seed_development_transformations
from app.main import app
from app.models.family import Family
from app.models.food_catalog import Recipe


def _override_db(db_session: Session):
    def override_get_db():
        yield db_session

    return override_get_db


def test_meal_transformation_endpoint_returns_improving_proposal(db_session: Session) -> None:
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

    recipe = db_session.query(Recipe).filter_by(
        recipe_key="breakfast:recipe:yogurt-muesli-banana"
    ).one()

    app.dependency_overrides[get_db] = _override_db(db_session)
    try:
        with TestClient(app) as client:
            response = client.post(
                f"/api/persons/{DEMO_PERSON_ID}/meal-transformations/proposals",
                json={
                    "planning_date": demo.planning_date.isoformat(),
                    "meal_type": "breakfast",
                    "recipe_id": str(recipe.id),
                    "quantity": "1",
                    "quantity_unit": "serving",
                    "daily_nutrition_state_id": str(demo.daily_nutrition_state_id),
                    "max_proposals": 5,
                },
            )

        assert response.status_code == 200
        payload = response.json()
        assert payload["baseline_fit"]["eligible"] is False
        assert payload["proposals"]
        proposal = payload["proposals"][0]
        assert proposal["operation"]["source_food_name"] == "Iogurte natural"
        assert proposal["operation"]["replacement_food_name"] == "Iogurte grego"
        assert proposal["resolves_mandatory_block"] is True
        assert proposal["after_fit"]["eligible"] is True
        assert proposal["after_fit"]["fit_score"] == "1.0000"
    finally:
        app.dependency_overrides.clear()
