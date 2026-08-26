from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from app.models.food_catalog import FoodCompositionSnapshot, RecipeCompositionSnapshot
from app.models.meal import Serving, ServingNutritionComponent

ENERGY_QUANTUM = Decimal("0.01")
NUTRIENT_QUANTUM = Decimal("0.0001")

_MASS_TO_GRAMS = {
    "mg": Decimal("0.001"),
    "g": Decimal(1),
    "kg": Decimal(1000),
}
_VOLUME_TO_MILLILITERS = {
    "ml": Decimal(1),
    "l": Decimal(1000),
}


@dataclass(frozen=True)
class NutrientSnapshot:
    value: Decimal
    unit: str


@dataclass(frozen=True)
class NutritionSnapshot:
    energy_kcal: Decimal | None
    nutrients: dict[str, NutrientSnapshot]


class ServingNutritionCalculationError(ValueError):
    pass


class UnsupportedUnitConversionError(ServingNutritionCalculationError):
    pass


class CatalogReferenceMismatchError(ServingNutritionCalculationError):
    pass


def convert_quantity(value: Decimal, from_unit: str, to_unit: str) -> Decimal:
    if from_unit == to_unit:
        return value

    if from_unit in _MASS_TO_GRAMS and to_unit in _MASS_TO_GRAMS:
        grams = value * _MASS_TO_GRAMS[from_unit]
        return grams / _MASS_TO_GRAMS[to_unit]

    if from_unit in _VOLUME_TO_MILLILITERS and to_unit in _VOLUME_TO_MILLILITERS:
        milliliters = value * _VOLUME_TO_MILLILITERS[from_unit]
        return milliliters / _VOLUME_TO_MILLILITERS[to_unit]

    raise UnsupportedUnitConversionError(
        f"Cannot safely convert serving quantity from {from_unit!r} to {to_unit!r}."
    )


def _scale_value(value: Decimal | None, factor: Decimal, quantum: Decimal) -> Decimal | None:
    if value is None:
        return None
    return (value * factor).quantize(quantum, rounding=ROUND_HALF_UP)


def scale_composition_nutrition(
    composition: FoodCompositionSnapshot | RecipeCompositionSnapshot,
    *,
    quantity: Decimal,
    quantity_unit: str,
) -> NutritionSnapshot:
    reference_quantity = convert_quantity(
        quantity,
        quantity_unit,
        composition.reference_unit,
    )
    factor = reference_quantity / composition.reference_quantity

    return NutritionSnapshot(
        energy_kcal=_scale_value(composition.energy_kcal, factor, ENERGY_QUANTUM),
        nutrients={
            nutrient.nutrient_key: NutrientSnapshot(
                value=_scale_value(nutrient.value, factor, NUTRIENT_QUANTUM)
                or Decimal(0),
                unit=nutrient.unit,
            )
            for nutrient in composition.nutrients
        },
    )


def _same_catalog_object(left: object | None, right: object | None) -> bool:
    if left is None or right is None:
        return False
    if left is right:
        return True

    left_id = getattr(left, "id", None)
    right_id = getattr(right, "id", None)
    return left_id is not None and left_id == right_id


def _bind_composition(
    serving: Serving,
    composition: FoodCompositionSnapshot | RecipeCompositionSnapshot,
) -> None:
    if isinstance(composition, FoodCompositionSnapshot):
        if serving.recipe is not None or serving.recipe_id is not None:
            raise CatalogReferenceMismatchError(
                "A recipe serving cannot be calculated from a food-item composition snapshot."
            )
        if serving.food_item is not None and not _same_catalog_object(
            serving.food_item, composition.food_item
        ):
            raise CatalogReferenceMismatchError(
                "The food composition snapshot does not belong to the serving's food item."
            )
        serving.food_item = composition.food_item
        serving.food_composition_snapshot = composition
        serving.recipe_composition_snapshot = None
        return

    if serving.food_item is not None or serving.food_item_id is not None:
        raise CatalogReferenceMismatchError(
            "A food-item serving cannot be calculated from a recipe composition snapshot."
        )
    if serving.recipe is not None and not _same_catalog_object(serving.recipe, composition.recipe):
        raise CatalogReferenceMismatchError(
            "The recipe composition snapshot does not belong to the serving's recipe."
        )
    serving.recipe = composition.recipe
    serving.recipe_composition_snapshot = composition
    serving.food_composition_snapshot = None


def _sync_nutrition_components(
    serving: Serving,
    composition: FoodCompositionSnapshot | RecipeCompositionSnapshot,
    *,
    snapshots: dict[str, NutritionSnapshot | None],
) -> None:
    existing = {component.nutrient_key: component for component in serving.nutrition_components}
    target_keys: set[str] = set()

    for nutrient in composition.nutrients:
        nutrient_key = nutrient.nutrient_key
        target_keys.add(nutrient_key)
        component = existing.get(nutrient_key)
        if component is None:
            component = ServingNutritionComponent(nutrient_key=nutrient_key)
            serving.nutrition_components.append(component)

        component.planned_value = (
            snapshots["planned"].nutrients[nutrient_key].value
            if snapshots["planned"] is not None
            else None
        )
        component.served_value = (
            snapshots["served"].nutrients[nutrient_key].value
            if snapshots["served"] is not None
            else None
        )
        component.consumed_value = (
            snapshots["consumed"].nutrients[nutrient_key].value
            if snapshots["consumed"] is not None
            else None
        )
        component.unit = nutrient.unit

    for component in list(serving.nutrition_components):
        if component.nutrient_key not in target_keys:
            serving.nutrition_components.remove(component)


def calculate_serving_nutrition(
    serving: Serving,
    composition: FoodCompositionSnapshot | RecipeCompositionSnapshot,
    *,
    calculation_version: str = "serving-nutrition-v1",
) -> Serving:
    if serving.quantity_unit is None:
        raise ServingNutritionCalculationError(
            "Serving quantity_unit is required for catalogue nutrition calculation."
        )

    quantities = {
        "planned": serving.quantity_planned,
        "served": serving.quantity_served,
        "consumed": serving.quantity_consumed,
    }
    if all(quantity is None for quantity in quantities.values()):
        raise ServingNutritionCalculationError(
            "At least one serving quantity is required for catalogue nutrition calculation."
        )

    snapshots = {
        stage: (
            scale_composition_nutrition(
                composition,
                quantity=quantity,
                quantity_unit=serving.quantity_unit,
            )
            if quantity is not None
            else None
        )
        for stage, quantity in quantities.items()
    }

    _bind_composition(serving, composition)

    serving.energy_planned_kcal = (
        snapshots["planned"].energy_kcal if snapshots["planned"] is not None else None
    )
    serving.energy_served_kcal = (
        snapshots["served"].energy_kcal if snapshots["served"] is not None else None
    )
    serving.energy_consumed_kcal = (
        snapshots["consumed"].energy_kcal if snapshots["consumed"] is not None else None
    )

    _sync_nutrition_components(
        serving,
        composition,
        snapshots=snapshots,
    )

    serving.nutrition_source = "catalog"
    serving.nutrition_calculation_version = calculation_version
    return serving
