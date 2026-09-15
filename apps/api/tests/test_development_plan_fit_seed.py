from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.demo_seed import DEMO_PERSON_ID, seed_demo_dataset
from app.development_breakfast_seed import seed_development_breakfast_catalog
from app.development_plan_fit_seed import PLAN_ID, seed_development_plan_fit
from app.models.family import Family
from app.models.food_catalog import Recipe, RecipeCompositionSnapshot
from app.schemas.meal_plan_fit import MealPlanFitCreate
from app.schemas.meal_recommendation import MealRecommendationCandidateInput
from app.services.meal_plan_fit import evaluate_meal_plan_fit


def test_development_plan_fit_seed_is_idempotent_and_evaluable(db_session: Session) -> None:
    demo = seed_demo_dataset(
        db_session,
        now=datetime(2026, 9, 15, 12, 0, tzinfo=UTC),
    )
    family = db_session.get(Family, demo.family_id)
    assert family is not None
    seed_development_breakfast_catalog(db_session, families=(family,))

    first = seed_development_plan_fit(db_session, person_id=DEMO_PERSON_ID)
    second = seed_development_plan_fit(db_session, person_id=DEMO_PERSON_ID)
    db_session.commit()

    assert first.plan_id == PLAN_ID
    assert second.plan_id == PLAN_ID
    assert first.rule_count == 2

    recipe = db_session.query(Recipe).filter_by(
        recipe_key="breakfast:recipe:greek-yogurt-muesli-berries"
    ).one()
    composition = db_session.query(RecipeCompositionSnapshot).filter_by(
        recipe_id=recipe.id,
        composition_version="breakfast-estimate-v1",
    ).one()

    fit = evaluate_meal_plan_fit(
        db_session,
        person_id=DEMO_PERSON_ID,
        data=MealPlanFitCreate(
            planning_date=demo.planning_date,
            meal_type="breakfast",
            daily_nutrition_state_id=demo.daily_nutrition_state_id,
            candidate=MealRecommendationCandidateInput(
                candidate_kind="recipe",
                composition_id=composition.id,
                quantity=Decimal(1),
                quantity_unit="serving",
            ),
        ),
    )

    assert fit.status == "pass"
    assert fit.eligible is True
    assert fit.fit_score == Decimal("1.0000")
    assert fit.active_plans[0].title == "Plano alimentar demo — pequeno-almoço"
    assert {rule.target_key for rule in fit.rule_results if rule.scope == "meal"} == {
        "protein",
        "fiber",
    }
