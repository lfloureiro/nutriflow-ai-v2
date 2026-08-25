import json
import re
import unicodedata
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.food_catalog import FoodCompositionSnapshot, FoodItem, Recipe, RecipeIngredient
from app.services.fooddata_central import (
    FdcFoodNutrition,
    FdcFoodPortion,
    FoodDataCentralError,
    fetch_food_nutrition,
    search_foods,
)
from app.services.serving_nutrition import UnsupportedUnitConversionError, convert_quantity
from app.services.shared_ingredient_enrichment import (
    apply_fdc_portion_conversion_to_shared_ingredient,
)

_VOLUME_ML = {
    "cup": Decimal(240),
    "cups": Decimal(240),
    "tbsp": Decimal(15),
    "tablespoon": Decimal(15),
    "tablespoons": Decimal(15),
    "tsp": Decimal(5),
    "teaspoon": Decimal(5),
    "teaspoons": Decimal(5),
}
_VOLUME_PRIORITY = {"cup": 0, "cups": 0, "tbsp": 1, "tablespoon": 1, "tablespoons": 1}
_VOLUME_PRIORITY.update({"tsp": 2, "teaspoon": 2, "teaspoons": 2})


@dataclass(frozen=True)
class AutomaticUnitConversionSpec:
    ingredient_name: str
    recipe_unit: str
    query: str
    expected_description: str
    portion_markers: tuple[str, ...] = ()
    volume_measure: bool = False


@dataclass(frozen=True)
class AutomaticUnitConversionResult:
    catalog_key: str
    ingredient_name: str
    recipe_unit: str
    fdc_id: int
    portion_id: int
    created: bool
    recalculated_recipe_count: int


_SPECS = (
    AutomaticUnitConversionSpec(
        ingredient_name="Azeite",
        recipe_unit="ml",
        query="oil olive salad or cooking",
        expected_description="Oil, olive, salad or cooking",
        volume_measure=True,
    ),
    AutomaticUnitConversionSpec(
        ingredient_name="Alho",
        recipe_unit="un",
        query="garlic raw",
        expected_description="Garlic, raw",
        portion_markers=("clove",),
    ),
    AutomaticUnitConversionSpec(
        ingredient_name="Cebolas",
        recipe_unit="un",
        query="onions raw",
        expected_description="Onions, raw",
        portion_markers=("medium",),
    ),
    AutomaticUnitConversionSpec(
        ingredient_name="Ovos",
        recipe_unit="un",
        query="egg whole raw fresh",
        expected_description="Egg, whole, raw, fresh",
        portion_markers=("large",),
    ),
    AutomaticUnitConversionSpec(
        ingredient_name="Limão",
        recipe_unit="un",
        query="lemons raw without peel",
        expected_description="Lemons, raw, without peel",
        portion_markers=("fruit",),
    ),
    AutomaticUnitConversionSpec(
        ingredient_name="Cenouras",
        recipe_unit="un",
        query="carrots raw",
        expected_description="Carrots, raw",
        portion_markers=("medium",),
    ),
    AutomaticUnitConversionSpec(
        ingredient_name="Pimento verde",
        recipe_unit="un",
        query="peppers sweet green raw",
        expected_description="Peppers, sweet, green, raw",
        portion_markers=("medium",),
    ),
    AutomaticUnitConversionSpec(
        ingredient_name="Pimento vermelho",
        recipe_unit="un",
        query="peppers sweet red raw",
        expected_description="Peppers, sweet, red, raw",
        portion_markers=("medium",),
    ),
)


def _normalized(value: str) -> str:
    text = unicodedata.normalize("NFKD", value.casefold())
    text = "".join(character for character in text if not unicodedata.combining(character))
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def _recipe_units_by_food_item(db: Session) -> dict[object, set[str]]:
    rows = db.execute(
        select(RecipeIngredient.food_item_id, RecipeIngredient.unit)
        .join(Recipe, Recipe.id == RecipeIngredient.recipe_id)
        .where(Recipe.is_active.is_(True))
    ).all()
    result: dict[object, set[str]] = {}
    for food_item_id, unit in rows:
        result.setdefault(food_item_id, set()).add(unit.strip().casefold())
    return result


def _shared_ingredients(db: Session) -> list[FoodItem]:
    return list(
        db.scalars(
            select(FoodItem)
            .options(
                selectinload(FoodItem.compositions).selectinload(
                    FoodCompositionSnapshot.nutrients
                )
            )
            .where(
                FoodItem.family_id.is_(None),
                FoodItem.food_kind == "ingredient",
                FoodItem.is_active.is_(True),
            )
            .order_by(FoodItem.name, FoodItem.id)
        ).all()
    )


def _has_conversion(composition: FoodCompositionSnapshot, recipe_unit: str) -> bool:
    if not composition.notes:
        return False
    try:
        payload = json.loads(composition.notes)
    except json.JSONDecodeError:
        return False
    if not isinstance(payload, dict):
        return False
    conversions = payload.get("portion_conversions")
    return isinstance(conversions, dict) and recipe_unit in conversions


def _conversion_needed(
    item: FoodItem,
    *,
    recipe_unit: str,
) -> bool:
    if not item.compositions:
        return False
    latest = item.compositions[-1]
    if latest.energy_kcal is None or _has_conversion(latest, recipe_unit):
        return False
    try:
        convert_quantity(Decimal(1), recipe_unit, latest.reference_unit)
    except UnsupportedUnitConversionError:
        return latest.reference_unit.strip().casefold() in {"g", "kg"}
    return False


def _matching_food(spec: AutomaticUnitConversionSpec) -> FdcFoodNutrition | None:
    expected = _normalized(spec.expected_description)
    results = search_foods(spec.query, limit=8)
    matches = [result for result in results if _normalized(result.description) == expected]
    if not matches:
        return None
    matches.sort(key=lambda result: (result.data_type != "Foundation", result.fdc_id))
    food = fetch_food_nutrition(matches[0].fdc_id)
    if _normalized(food.description) != expected:
        return None
    return food


def _portion_text(portion: FdcFoodPortion) -> str:
    return _normalized(
        " ".join(
            value
            for value in (
                portion.description,
                portion.measure_unit,
                portion.modifier,
            )
            if value
        )
    )


def _unit_portion(
    food: FdcFoodNutrition,
    spec: AutomaticUnitConversionSpec,
) -> tuple[FdcFoodPortion, Decimal | None] | None:
    if spec.volume_measure:
        choices: list[tuple[int, int, FdcFoodPortion, Decimal]] = []
        for portion in food.portions:
            measure = (portion.measure_unit or "").strip().casefold()
            ml_per_measure = _VOLUME_ML.get(measure)
            if ml_per_measure is None:
                continue
            total_ml = portion.amount * ml_per_measure
            choices.append(
                (
                    _VOLUME_PRIORITY[measure],
                    portion.portion_id,
                    portion,
                    total_ml,
                )
            )
        if not choices:
            return None
        choices.sort(key=lambda choice: (choice[0], choice[1]))
        _, _, portion, total_ml = choices[0]
        return portion, total_ml

    choices = [
        portion
        for portion in food.portions
        if any(marker in _portion_text(portion) for marker in spec.portion_markers)
    ]
    if not choices:
        return None
    choices.sort(key=lambda portion: (portion.amount != Decimal(1), portion.portion_id))
    return choices[0], None


def auto_enrich_shared_unit_conversions(
    db: Session,
) -> tuple[AutomaticUnitConversionResult, ...]:
    units_by_item = _recipe_units_by_food_item(db)
    specs_by_name = {_normalized(spec.ingredient_name): spec for spec in _SPECS}
    results: list[AutomaticUnitConversionResult] = []

    for item in _shared_ingredients(db):
        spec = specs_by_name.get(_normalized(item.name))
        if spec is None or item.id is None:
            continue
        if spec.recipe_unit not in units_by_item.get(item.id, set()):
            continue
        if not _conversion_needed(item, recipe_unit=spec.recipe_unit):
            continue

        try:
            food = _matching_food(spec)
            if food is None:
                continue
            selected = _unit_portion(food, spec)
        except FoodDataCentralError:
            break
        if selected is None:
            continue
        portion, recipe_unit_quantity = selected
        enrichment = apply_fdc_portion_conversion_to_shared_ingredient(
            db,
            catalog_key=item.catalog_key,
            food=food,
            unit_portion=portion,
            recipe_unit=spec.recipe_unit,
            recipe_unit_quantity=recipe_unit_quantity,
            estimated=True,
        )
        results.append(
            AutomaticUnitConversionResult(
                catalog_key=item.catalog_key,
                ingredient_name=item.name,
                recipe_unit=spec.recipe_unit,
                fdc_id=food.fdc_id,
                portion_id=portion.portion_id,
                created=enrichment.created,
                recalculated_recipe_count=len(enrichment.recalculated_recipe_ids),
            )
        )

    return tuple(results)
