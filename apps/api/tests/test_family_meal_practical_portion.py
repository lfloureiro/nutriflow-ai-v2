from decimal import Decimal

from app.models.food_catalog import Recipe, RecipeCompositionSnapshot
from app.services.family_meal_plan import _default_recipe_portion


def test_family_planning_uses_practical_serving_reference_when_source_servings_are_missing() -> None:
    recipe = Recipe(recipe_key="test:recipe", name="Test recipe", source="test")
    recipe.compositions.append(
        RecipeCompositionSnapshot(
            reference_quantity=Decimal(4),
            reference_unit="serving",
            energy_kcal=Decimal(2000),
            composition_version="test-v1",
            calculation_version="recipe-nutrition-v3",
        )
    )

    assert _default_recipe_portion(recipe) == (Decimal(1), "serving")


def test_explicit_recipe_serving_count_still_has_priority() -> None:
    recipe = Recipe(
        recipe_key="test:recipe-explicit",
        name="Test recipe explicit",
        source="test",
        serving_count=Decimal(6),
    )

    assert _default_recipe_portion(recipe) == (Decimal(1), "serving")
