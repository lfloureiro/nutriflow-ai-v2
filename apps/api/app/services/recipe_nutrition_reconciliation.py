from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.food_catalog import (
    FoodCompositionSnapshot,
    FoodItem,
    Recipe,
    RecipeCompositionSnapshot,
    RecipeIngredient,
)
from app.services.recipe_nutrition import CALCULATION_VERSION, build_recipe_composition

CURRENT_EVIDENCE_POLICY_VERSION = "recipe-evidence-v3"


@dataclass(frozen=True)
class LegacyRecipeNutritionCoverage:
    total_count: int
    rebuilt_count: int
    calculated_count: int
    estimated_count: int
    blocked_count: int


def _legacy_recipes(db: Session) -> list[Recipe]:
    return list(
        db.scalars(
            select(Recipe)
            .options(
                selectinload(Recipe.ingredients)
                .selectinload(RecipeIngredient.food_item)
                .selectinload(FoodItem.compositions)
                .selectinload(FoodCompositionSnapshot.nutrients),
                selectinload(Recipe.compositions),
            )
            .where(
                Recipe.source == "legacy-v1",
                Recipe.is_active.is_(True),
            )
            .order_by(Recipe.name, Recipe.id)
        )
        .unique()
        .all()
    )


def _latest_calculated(recipe: Recipe) -> RecipeCompositionSnapshot | None:
    return next(
        (
            composition
            for composition in reversed(recipe.compositions)
            if composition.calculation_version == CALCULATION_VERSION
        ),
        None,
    )


def _expected_ingredient_inputs(recipe: Recipe) -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    for index, ingredient in enumerate(recipe.ingredients):
        composition = (
            ingredient.food_item.compositions[-1]
            if ingredient.food_item.compositions
            else None
        )
        result.append(
            {
                "sort_order": index,
                "food_catalog_key": ingredient.food_item.catalog_key,
                "quantity": str(ingredient.quantity),
                "unit": ingredient.unit,
                "composition_snapshot_id": str(composition.id) if composition else None,
                "composition_data_version": composition.data_version if composition else None,
            }
        )
    return result


def _snapshot_is_current(
    recipe: Recipe,
    composition: RecipeCompositionSnapshot | None,
) -> bool:
    if composition is None or not isinstance(composition.calculation_inputs, dict):
        return False
    inputs = composition.calculation_inputs
    if inputs.get("policy_version") != CURRENT_EVIDENCE_POLICY_VERSION:
        return False
    actual = inputs.get("ingredients")
    if not isinstance(actual, list):
        return False
    expected = _expected_ingredient_inputs(recipe)
    if len(actual) != len(expected):
        return False
    for actual_row, expected_row in zip(actual, expected, strict=True):
        if not isinstance(actual_row, dict):
            return False
        if any(actual_row.get(key) != value for key, value in expected_row.items()):
            return False
    return (
        inputs.get("serving_count")
        == (str(recipe.serving_count) if recipe.serving_count is not None else None)
        and inputs.get("yield_quantity")
        == (str(recipe.yield_quantity) if recipe.yield_quantity is not None else None)
        and inputs.get("yield_unit") == recipe.yield_unit
    )


def _is_estimated(composition: RecipeCompositionSnapshot) -> bool:
    inputs = composition.calculation_inputs
    return isinstance(inputs, dict) and inputs.get("energy_estimated") is True


def reconcile_legacy_recipe_nutrition(db: Session) -> LegacyRecipeNutritionCoverage:
    recipes = _legacy_recipes(db)
    rebuilt_count = 0
    for recipe in recipes:
        latest = _latest_calculated(recipe)
        if _snapshot_is_current(recipe, latest):
            continue
        build_recipe_composition(recipe)
        rebuilt_count += 1
    db.flush()

    calculated_count = 0
    estimated_count = 0
    blocked_count = 0
    for recipe in recipes:
        latest = _latest_calculated(recipe)
        if latest is None or latest.energy_kcal is None:
            blocked_count += 1
        elif _is_estimated(latest):
            estimated_count += 1
        else:
            calculated_count += 1

    return LegacyRecipeNutritionCoverage(
        total_count=len(recipes),
        rebuilt_count=rebuilt_count,
        calculated_count=calculated_count,
        estimated_count=estimated_count,
        blocked_count=blocked_count,
    )
