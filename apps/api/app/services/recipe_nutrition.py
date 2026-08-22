import uuid
from dataclasses import dataclass
from decimal import Decimal

from app.models.food_catalog import (
    FoodCompositionSnapshot,
    Recipe,
    RecipeCompositionSnapshot,
    RecipeNutrientComponent,
)
from app.services.serving_nutrition import (
    NutritionSnapshot,
    UnsupportedUnitConversionError,
    convert_quantity,
    scale_composition_nutrition,
)

CALCULATION_VERSION = "recipe-nutrition-v1"


@dataclass(frozen=True)
class RecipeNutritionBuildResult:
    composition: RecipeCompositionSnapshot
    issues: tuple[str, ...]


def _reference(recipe: Recipe) -> tuple[Decimal, str]:
    if recipe.yield_quantity is not None and recipe.yield_unit is not None:
        return recipe.yield_quantity, recipe.yield_unit
    if recipe.serving_count is not None:
        return recipe.serving_count, "serving"
    return Decimal(1), "recipe"


def _latest_food_composition(recipe_ingredient) -> FoodCompositionSnapshot | None:
    compositions = recipe_ingredient.food_item.compositions
    return compositions[-1] if compositions else None


def _aggregate_nutrients(
    snapshots: list[NutritionSnapshot],
    issues: list[str],
) -> list[RecipeNutrientComponent]:
    if not snapshots:
        return []

    nutrient_keys: set[str] = set()
    for snapshot in snapshots:
        nutrient_keys.update(snapshot.nutrients)

    components: list[RecipeNutrientComponent] = []
    for nutrient_key in sorted(nutrient_keys):
        if any(nutrient_key not in snapshot.nutrients for snapshot in snapshots):
            issues.append(
                f"Nutrient {nutrient_key!r} is missing from at least one ingredient composition."
            )
            continue

        first = next(
            snapshot.nutrients[nutrient_key]
            for snapshot in snapshots
            if nutrient_key in snapshot.nutrients
        )
        total = Decimal(0)
        compatible = True
        for snapshot in snapshots:
            nutrient = snapshot.nutrients[nutrient_key]
            try:
                total += convert_quantity(nutrient.value, nutrient.unit, first.unit)
            except UnsupportedUnitConversionError:
                compatible = False
                issues.append(
                    f"Nutrient {nutrient_key!r} uses incompatible units "
                    f"{nutrient.unit!r} and {first.unit!r}."
                )
                break
        if compatible:
            components.append(
                RecipeNutrientComponent(
                    nutrient_key=nutrient_key,
                    value=total,
                    unit=first.unit,
                )
            )
    return components


def build_recipe_composition(recipe: Recipe) -> RecipeNutritionBuildResult:
    """Create a new immutable composition snapshot from current Recipe ingredients.

    Missing or unsafe ingredient evidence is preserved as explicit issues. A snapshot is
    still created so the latest composition always corresponds to the current Recipe
    definition instead of silently falling back to stale nutrition.
    """

    issues: list[str] = []
    scaled: list[NutritionSnapshot] = []
    inputs: list[dict[str, str | int | None]] = []

    if not recipe.ingredients:
        issues.append("Recipe has no ingredients.")

    for index, ingredient in enumerate(recipe.ingredients):
        composition = _latest_food_composition(ingredient)
        inputs.append(
            {
                "sort_order": index,
                "recipe_ingredient_id": str(ingredient.id) if ingredient.id else None,
                "food_item_id": str(ingredient.food_item_id),
                "food_catalog_key": ingredient.food_item.catalog_key,
                "quantity": str(ingredient.quantity),
                "unit": ingredient.unit,
                "composition_snapshot_id": str(composition.id) if composition else None,
                "composition_data_version": composition.data_version if composition else None,
            }
        )
        if composition is None:
            issues.append(
                f"Ingredient {ingredient.food_item.name!r} has no nutrition composition."
            )
            continue
        try:
            scaled.append(
                scale_composition_nutrition(
                    composition,
                    quantity=ingredient.quantity,
                    quantity_unit=ingredient.unit,
                )
            )
        except UnsupportedUnitConversionError:
            issues.append(
                f"Ingredient {ingredient.food_item.name!r} cannot be safely converted "
                f"from {ingredient.unit!r} to {composition.reference_unit!r}."
            )

    all_ingredients_scaled = len(scaled) == len(recipe.ingredients) and bool(recipe.ingredients)
    energy_kcal: Decimal | None = None
    nutrients: list[RecipeNutrientComponent] = []

    if all_ingredients_scaled:
        if all(snapshot.energy_kcal is not None for snapshot in scaled):
            energy_kcal = sum(
                (snapshot.energy_kcal for snapshot in scaled if snapshot.energy_kcal is not None),
                start=Decimal(0),
            )
        else:
            issues.append("At least one ingredient is missing energy data.")
        nutrients = _aggregate_nutrients(scaled, issues)

    reference_quantity, reference_unit = _reference(recipe)
    composition = RecipeCompositionSnapshot(
        reference_quantity=reference_quantity,
        reference_unit=reference_unit,
        energy_kcal=energy_kcal,
        composition_version=f"calculated-{uuid.uuid4()}",
        calculation_version=CALCULATION_VERSION,
        calculation_inputs={
            "ingredients": inputs,
            "issues": issues,
            "serving_count": str(recipe.serving_count) if recipe.serving_count is not None else None,
            "yield_quantity": str(recipe.yield_quantity) if recipe.yield_quantity is not None else None,
            "yield_unit": recipe.yield_unit,
        },
    )
    composition.nutrients.extend(nutrients)
    recipe.compositions.append(composition)
    return RecipeNutritionBuildResult(composition=composition, issues=tuple(issues))
