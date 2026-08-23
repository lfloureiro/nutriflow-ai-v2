from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.development_breakfast_seed import seed_development_breakfast_catalog
from app.models.family import Family
from app.models.food_catalog import Recipe, RecipeCompositionSnapshot
from app.models.meal_candidate_planning_profile import MealCandidatePlanningProfile


def test_breakfast_catalog_is_shared_nutrition_ready_and_idempotent(
    db_session: Session,
) -> None:
    family = Family(name="Família Pequeno-almoço", timezone="Europe/Lisbon")
    db_session.add(family)
    db_session.flush()

    first = seed_development_breakfast_catalog(db_session, families=(family,))
    second = seed_development_breakfast_catalog(db_session, families=(family,))
    db_session.flush()

    assert first == second
    assert first.ingredient_count == 13
    assert first.recipe_count == 11

    recipes = list(
        db_session.scalars(
            select(Recipe).where(Recipe.source == "development-breakfast")
        ).all()
    )
    assert len(recipes) == 11
    assert all(recipe.family_id is None for recipe in recipes)
    assert all(recipe.serving_count == Decimal("1.00") for recipe in recipes)

    coffee = next(
        recipe
        for recipe in recipes
        if recipe.recipe_key == "breakfast:recipe:coffee-milk-butter-toast"
    )
    cerelac = next(
        recipe
        for recipe in recipes
        if recipe.recipe_key == "breakfast:recipe:cerelac-milk"
    )
    coffee_composition = db_session.scalar(
        select(RecipeCompositionSnapshot).where(
            RecipeCompositionSnapshot.recipe_id == coffee.id
        )
    )
    cerelac_composition = db_session.scalar(
        select(RecipeCompositionSnapshot).where(
            RecipeCompositionSnapshot.recipe_id == cerelac.id
        )
    )
    assert coffee_composition is not None
    assert cerelac_composition is not None
    assert coffee_composition.energy_kcal == Decimal("285.0000")
    assert cerelac_composition.energy_kcal == Decimal("305.0000")
    assert coffee_composition.calculation_inputs is not None
    assert coffee_composition.calculation_inputs["evidence_level"] == "estimated"

    profiles = list(
        db_session.scalars(
            select(MealCandidatePlanningProfile).where(
                MealCandidatePlanningProfile.family_id == family.id,
                MealCandidatePlanningProfile.source == "development-breakfast",
            )
        ).all()
    )
    assert len(profiles) == 11
    assert all(profile.suitable_meal_types == ["breakfast"] for profile in profiles)
    assert all(profile.planning_category == "breakfast" for profile in profiles)

    assert (
        db_session.scalar(
            select(func.count()).select_from(RecipeCompositionSnapshot).where(
                RecipeCompositionSnapshot.calculation_version
                == "development-breakfast-estimate-v1"
            )
        )
        == 11
    )
