import json
import uuid
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

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


@dataclass(frozen=True)
class IngredientPortionConversion:
    recipe_unit: str
    reference_unit: str
    quantity_in_reference_unit: Decimal
    source: str | None
    source_reference: str | None
    description: str | None


def _reference(recipe: Recipe) -> tuple[Decimal, str]:
    if recipe.yield_quantity is not None and recipe.yield_unit is not None:
        return recipe.yield_quantity, recipe.yield_unit
    if recipe.serving_count is not None:
        return recipe.serving_count, "serving"
    return Decimal(1), "recipe"


def _latest_food_composition(recipe_ingredient) -> FoodCompositionSnapshot | None:
    compositions = recipe_ingredient.food_item.compositions
    return compositions[-1] if compositions else None


def _portion_conversion(
    composition: FoodCompositionSnapshot,
    recipe_unit: str,
) -> IngredientPortionConversion | None:
    if not composition.notes:
        return None
    try:
        payload = json.loads(composition.notes)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    raw_conversions = payload.get("portion_conversions")
    if not isinstance(raw_conversions, dict):
        return None

    normalized_unit = recipe_unit.strip().casefold()
    raw = raw_conversions.get(normalized_unit)
    if not isinstance(raw, dict):
        return None
    reference_unit = raw.get("reference_unit")
    raw_quantity = raw.get("quantity_in_reference_unit")
    if not isinstance(reference_unit, str) or raw_quantity is None:
        return None
    try:
        quantity = Decimal(str(raw_quantity))
    except (InvalidOperation, TypeError, ValueError):
        return None
    if quantity <= 0:
        return None
    normalized_reference_unit = reference_unit.strip().casefold()
    if not normalized_reference_unit:
        return None
    source = raw.get("source")
    source_reference = raw.get("source_reference")
    description = raw.get("fdc_portion_description")
    return IngredientPortionConversion(
        recipe_unit=normalized_unit,
        reference_unit=normalized_reference_unit,
        quantity_in_reference_unit=quantity,
        source=source if isinstance(source, str) else None,
        source_reference=(
            source_reference if isinstance(source_reference, str) else None
        ),
        description=description if isinstance(description, str) else None,
    )


def _scale_recipe_ingredient(
    recipe_ingredient,
    composition: FoodCompositionSnapshot,
) -> tuple[NutritionSnapshot, IngredientPortionConversion | None]:
    try:
        return (
            scale_composition_nutrition(
                composition,
                quantity=recipe_ingredient.quantity,
                quantity_unit=recipe_ingredient.unit,
            ),
            None,
        )
    except UnsupportedUnitConversionError:
        conversion = _portion_conversion(composition, recipe_ingredient.unit)
        if conversion is None:
            raise
        converted_quantity = (
            recipe_ingredient.quantity * conversion.quantity_in_reference_unit
        )
        return (
            scale_composition_nutrition(
                composition,
                quantity=converted_quantity,
                quantity_unit=conversion.reference_unit,
            ),
            conversion,
        )


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
    inputs: list[dict[str, object]] = []

    if not recipe.ingredients:
        issues.append("Recipe has no ingredients.")

    for index, ingredient in enumerate(recipe.ingredients):
        composition = _latest_food_composition(ingredient)
        input_row: dict[str, object] = {
            "sort_order": index,
            "recipe_ingredient_id": str(ingredient.id) if ingredient.id else None,
            "food_item_id": (
                str(ingredient.food_item_id) if ingredient.food_item_id else None
            ),
            "food_catalog_key": ingredient.food_item.catalog_key,
            "quantity": str(ingredient.quantity),
            "unit": ingredient.unit,
            "composition_snapshot_id": str(composition.id) if composition else None,
            "composition_data_version": composition.data_version if composition else None,
        }
        inputs.append(input_row)
        if composition is None:
            issues.append(
                f"Ingredient {ingredient.food_item.name!r} has no nutrition composition."
            )
            continue
        try:
            snapshot, portion_conversion = _scale_recipe_ingredient(
                ingredient,
                composition,
            )
            scaled.append(snapshot)
            if portion_conversion is not None:
                input_row["portion_conversion"] = {
                    "recipe_unit": portion_conversion.recipe_unit,
                    "reference_unit": portion_conversion.reference_unit,
                    "quantity_in_reference_unit": str(
                        portion_conversion.quantity_in_reference_unit
                    ),
                    "source": portion_conversion.source,
                    "source_reference": portion_conversion.source_reference,
                    "description": portion_conversion.description,
                }
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
            "serving_count": (
                str(recipe.serving_count) if recipe.serving_count is not None else None
            ),
            "yield_quantity": (
                str(recipe.yield_quantity) if recipe.yield_quantity is not None else None
            ),
            "yield_unit": recipe.yield_unit,
        },
    )
    composition.nutrients.extend(nutrients)
    recipe.compositions.append(composition)
    return RecipeNutritionBuildResult(composition=composition, issues=tuple(issues))
