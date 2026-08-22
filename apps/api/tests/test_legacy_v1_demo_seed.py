from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.demo_seed import DEMO_FAMILY_ID, DEMO_PERSON_ID, seed_demo_dataset
from app.legacy_v1_demo_seed import (
    LEGACY_V1_SOURCE,
    LEGACY_V1_SOURCE_REFERENCE,
    SYNTHETIC_NUTRITION_NOTE,
    seed_legacy_v1_demo_catalog,
)
from app.models.family import Family
from app.models.food_catalog import FoodItem, Recipe
from app.schemas.meal_recommendation import MealRecommendationCandidateInput
from app.services.meal_recommendation import recommend_meals
from app.services.meal_recommendation_api import load_recommendation_inputs
from app.services.planning_bootstrap_api import get_planning_bootstrap
from app.services.recipe_catalogue import list_family_recipes

NOW = datetime(2026, 8, 22, 18, 30, tzinfo=UTC)


def test_legacy_v1_demo_catalog_is_idempotent_and_recommendation_ready(
    db_session: Session,
) -> None:
    demo = seed_demo_dataset(db_session, now=NOW)
    db_session.flush()
    family = db_session.get(Family, DEMO_FAMILY_ID)
    assert family is not None

    first = seed_legacy_v1_demo_catalog(db_session, family=family, now=NOW)
    second = seed_legacy_v1_demo_catalog(db_session, family=family, now=NOW)
    db_session.flush()

    assert first == second
    assert first.ingredient_count == 24
    assert first.recipe_count == 5

    ingredient_count = db_session.scalar(
        select(func.count())
        .select_from(FoodItem)
        .where(
            FoodItem.family_id == DEMO_FAMILY_ID,
            FoodItem.source == LEGACY_V1_SOURCE,
            FoodItem.food_kind == "ingredient",
        )
    )
    recipe_count = db_session.scalar(
        select(func.count())
        .select_from(Recipe)
        .where(
            Recipe.family_id == DEMO_FAMILY_ID,
            Recipe.source == LEGACY_V1_SOURCE,
        )
    )
    assert ingredient_count == 24
    assert recipe_count == 5

    ingredients = db_session.scalars(
        select(FoodItem).where(
            FoodItem.family_id == DEMO_FAMILY_ID,
            FoodItem.source == LEGACY_V1_SOURCE,
        )
    ).all()
    assert all(item.source_reference == LEGACY_V1_SOURCE_REFERENCE for item in ingredients)
    assert all(item.compositions == [] for item in ingredients)

    recipes = list_family_recipes(db_session, DEMO_FAMILY_ID)
    legacy_recipes = [recipe for recipe in recipes if recipe.source == LEGACY_V1_SOURCE]
    assert {recipe.name for recipe in legacy_recipes} == {
        "Arroz de frango no forno",
        "Caril suave de frango",
        "Chili con carne",
        "Esparguete à bolonhesa",
        "Salmão no forno com legumes",
    }
    assert all(recipe.serving_count == 4 for recipe in legacy_recipes)
    assert all(recipe.latest_composition is not None for recipe in legacy_recipes)
    assert all(
        recipe.latest_composition.energy_kcal is not None
        and recipe.latest_composition.energy_kcal > 0
        for recipe in legacy_recipes
    )
    assert all(
        {nutrient.key for nutrient in recipe.latest_composition.nutrients}
        == {"fiber", "protein", "sodium"}
        for recipe in legacy_recipes
    )
    assert all(recipe.nutrition_issues == [SYNTHETIC_NUTRITION_NOTE] for recipe in legacy_recipes)

    bootstrap = get_planning_bootstrap(
        db_session,
        person_id=DEMO_PERSON_ID,
        scheduled_at=NOW,
    )
    legacy_candidates = [
        candidate
        for candidate in bootstrap.candidates
        if candidate.catalog_key.startswith("legacy-v1:recipe:")
    ]
    assert len(legacy_candidates) == 5
    assert all(candidate.reference_quantity == Decimal(1) for candidate in legacy_candidates)
    assert all(candidate.reference_unit == "serving" for candidate in legacy_candidates)
    assert all(
        candidate.energy_kcal is not None and candidate.energy_kcal > 0
        for candidate in legacy_candidates
    )

    candidate_inputs = [
        MealRecommendationCandidateInput(
            candidate_kind=candidate.candidate_kind,
            composition_id=candidate.composition_id,
            quantity=candidate.reference_quantity,
            quantity_unit=candidate.reference_unit,
        )
        for candidate in legacy_candidates
    ]
    person, state, meal_candidates = load_recommendation_inputs(
        db_session,
        person_id=DEMO_PERSON_ID,
        daily_nutrition_state_id=demo.daily_nutrition_state_id,
        planning_date=demo.planning_date,
        candidates=candidate_inputs,
    )
    recommendation = recommend_meals(
        daily_state=state,
        candidates=meal_candidates,
        preferences=list(person.food_preferences),
        adverse_reactions=list(person.food_adverse_reactions),
        constraints=list(person.nutrition_constraints),
        planning_date=demo.planning_date,
    )
    assert len(recommendation.eligible) == 5
    assert all(evaluation.candidate.quantity == Decimal(1) for evaluation in recommendation.eligible)
