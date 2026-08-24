import json
import uuid
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.food_catalog import (
    FoodCompositionSnapshot,
    FoodItem,
    Recipe,
    RecipeIngredient,
)
from app.services.serving_nutrition import (
    UnsupportedUnitConversionError,
    convert_quantity,
)

NutritionEnrichmentStatus = Literal[
    "missing_composition",
    "missing_energy",
    "missing_unit_conversion",
    "ready",
]


@dataclass(frozen=True)
class SharedIngredientEnrichmentAuditItem:
    catalog_key: str
    name: str
    source: str
    recipe_usage_count: int
    recipe_units: tuple[str, ...]
    status: NutritionEnrichmentStatus
    blocking_units: tuple[str, ...]
    reference_unit: str | None
    composition_source: str | None
    composition_source_reference: str | None


def _latest_composition(item: FoodItem) -> FoodCompositionSnapshot | None:
    return item.compositions[-1] if item.compositions else None


def _portion_conversion_reference_unit(
    composition: FoodCompositionSnapshot,
    recipe_unit: str,
) -> str | None:
    if not composition.notes:
        return None
    try:
        payload = json.loads(composition.notes)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    conversions = payload.get("portion_conversions")
    if not isinstance(conversions, dict):
        return None
    raw = conversions.get(recipe_unit.strip().casefold())
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
    normalized = reference_unit.strip().casefold()
    return normalized or None


def _composition_supports_unit(
    composition: FoodCompositionSnapshot,
    recipe_unit: str,
) -> bool:
    try:
        convert_quantity(Decimal(1), recipe_unit, composition.reference_unit)
        return True
    except UnsupportedUnitConversionError:
        reference_unit = _portion_conversion_reference_unit(composition, recipe_unit)
        if reference_unit is None:
            return False
        try:
            convert_quantity(Decimal(1), reference_unit, composition.reference_unit)
        except UnsupportedUnitConversionError:
            return False
        return True


def build_shared_ingredient_enrichment_audit(
    db: Session,
) -> list[SharedIngredientEnrichmentAuditItem]:
    ingredients = list(
        db.scalars(
            select(FoodItem)
            .options(selectinload(FoodItem.compositions))
            .where(
                FoodItem.family_id.is_(None),
                FoodItem.food_kind == "ingredient",
                FoodItem.is_active.is_(True),
            )
            .order_by(FoodItem.name, FoodItem.id)
        ).all()
    )

    recipe_units: dict[uuid.UUID, set[str]] = defaultdict(set)
    recipe_ids: dict[uuid.UUID, set[uuid.UUID]] = defaultdict(set)
    usage_rows = db.execute(
        select(
            RecipeIngredient.food_item_id,
            RecipeIngredient.unit,
            RecipeIngredient.recipe_id,
        )
        .join(Recipe, Recipe.id == RecipeIngredient.recipe_id)
        .where(Recipe.is_active.is_(True))
    ).all()
    for ingredient_id, unit, recipe_id in usage_rows:
        recipe_units[ingredient_id].add(unit.strip().casefold())
        recipe_ids[ingredient_id].add(recipe_id)

    result: list[SharedIngredientEnrichmentAuditItem] = []
    for item in ingredients:
        composition = _latest_composition(item)
        units = tuple(sorted(recipe_units.get(item.id, set())))
        blocking_units: tuple[str, ...] = ()
        status: NutritionEnrichmentStatus
        if composition is None:
            status = "missing_composition"
        elif composition.energy_kcal is None:
            status = "missing_energy"
        else:
            blocking_units = tuple(
                unit
                for unit in units
                if not _composition_supports_unit(composition, unit)
            )
            status = "missing_unit_conversion" if blocking_units else "ready"

        result.append(
            SharedIngredientEnrichmentAuditItem(
                catalog_key=item.catalog_key,
                name=item.name,
                source=item.source,
                recipe_usage_count=len(recipe_ids.get(item.id, set())),
                recipe_units=units,
                status=status,
                blocking_units=blocking_units,
                reference_unit=(
                    composition.reference_unit if composition is not None else None
                ),
                composition_source=(
                    composition.source if composition is not None else None
                ),
                composition_source_reference=(
                    composition.source_reference if composition is not None else None
                ),
            )
        )

    status_priority: dict[NutritionEnrichmentStatus, int] = {
        "missing_composition": 0,
        "missing_energy": 1,
        "missing_unit_conversion": 2,
        "ready": 3,
    }
    return sorted(
        result,
        key=lambda item: (
            status_priority[item.status],
            -item.recipe_usage_count,
            item.name.casefold(),
        ),
    )
