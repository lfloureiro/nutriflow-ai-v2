from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.development_breakfast_seed import seed_development_breakfast_catalog
from app.development_snack_seed import seed_development_snack_catalog
from app.models.family import Family
from app.models.food_catalog import Recipe, RecipeCompositionSnapshot
from app.models.meal_candidate_planning_profile import MealCandidatePlanningProfile


def test_snack_catalog_is_shared_nutrition_ready_and_idempotent(
    db_session: Session,
) -> None:
    family = Family(name="Família Lanche", timezone="Europe/Lisbon")
    db_session.add(family)
    db_session.flush()
    seed_development_breakfast_catalog(db_session, families=(family,))

    first = seed_development_snack_catalog(db_session, families=(family,))
    second = seed_development_snack_catalog(db_session, families=(family,))
    db_session.flush()

    assert first == second
    assert first.new_ingredient_count == 4
    assert first.recipe_count == 12

    recipes = list(
        db_session.scalars(
            select(Recipe).where(Recipe.source == "development-snack")
        ).all()
    )
    assert len(recipes) == 12
    assert all(recipe.family_id is None for recipe in recipes)
    assert all(recipe.serving_count == Decimal("1.00") for recipe in recipes)

    mixed_toast = next(
        recipe
        for recipe in recipes
        if recipe.recipe_key == "snack:recipe:ham-cheese-toast"
    )
    composition = db_session.scalar(
        select(RecipeCompositionSnapshot).where(
            RecipeCompositionSnapshot.recipe_id == mixed_toast.id
        )
    )
    assert composition is not None
    assert composition.energy_kcal == Decimal("290.0000")
    assert composition.calculation_inputs is not None
    assert composition.calculation_inputs["evidence_level"] == "estimated"

    snack_profiles = list(
        db_session.scalars(
            select(MealCandidatePlanningProfile).where(
                MealCandidatePlanningProfile.family_id == family.id,
                MealCandidatePlanningProfile.source == "development-snack",
            )
        ).all()
    )
    assert len(snack_profiles) == 12
    assert all(profile.suitable_meal_types == ["snack"] for profile in snack_profiles)
    assert all(profile.planning_category == "snack" for profile in snack_profiles)

    breakfast_profiles = list(
        db_session.scalars(
            select(MealCandidatePlanningProfile).where(
                MealCandidatePlanningProfile.family_id == family.id,
                MealCandidatePlanningProfile.source == "development-breakfast",
            )
        ).all()
    )
    assert len(breakfast_profiles) == 11
    assert all(profile.suitable_meal_types == ["breakfast"] for profile in breakfast_profiles)

    assert (
        db_session.scalar(
            select(func.count()).select_from(RecipeCompositionSnapshot).where(
                RecipeCompositionSnapshot.calculation_version
                == "development-snack-estimate-v1"
            )
        )
        == 12
    )
