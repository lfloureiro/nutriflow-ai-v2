import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.food_catalog import (
    FoodCompositionSnapshot,
    FoodItem,
    FoodNutrientComponent,
    Recipe,
    RecipeIngredient,
)
from app.services.fooddata_central import (
    GENERIC_DATA_TYPES,
    FdcFoodNutrition,
    FdcFoodPortion,
)
from app.services.recipe_nutrition import build_recipe_composition


class SharedIngredientEnrichmentError(ValueError):
    pass


@dataclass(frozen=True)
class SharedIngredientEnrichmentResult:
    ingredient_id: uuid.UUID
    catalog_key: str
    composition_id: uuid.UUID
    data_version: str
    created: bool
    recalculated_recipe_ids: tuple[uuid.UUID, ...]


def _normalized_recipe_unit(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().casefold()
    return normalized or None


def _decimal_token(value: Decimal) -> str:
    return format(value.normalize(), "f").replace(".", "_")


def _effective_recipe_unit_quantity(
    unit_portion: FdcFoodPortion,
    recipe_unit_quantity: Decimal | None,
) -> Decimal:
    return recipe_unit_quantity or unit_portion.amount


def _data_version(
    food: FdcFoodNutrition,
    *,
    unit_portion: FdcFoodPortion | None,
    recipe_unit: str | None,
    recipe_unit_quantity: Decimal | None,
) -> str:
    publication = (food.publication_date or "unknown").replace("/", "-")
    portion_suffix = ""
    if unit_portion is not None and recipe_unit is not None:
        effective_quantity = _effective_recipe_unit_quantity(
            unit_portion,
            recipe_unit_quantity,
        )
        portion_suffix = (
            f"-p{unit_portion.portion_id}-{recipe_unit}"
            f"-q{_decimal_token(effective_quantity)}"
        )
    return f"usda-fdc-{food.fdc_id}-{publication}{portion_suffix}"[:64]


def _shared_ingredient(
    db: Session,
    *,
    catalog_key: str,
) -> FoodItem:
    item = db.scalar(
        select(FoodItem)
        .options(
            selectinload(FoodItem.compositions).selectinload(
                FoodCompositionSnapshot.nutrients
            )
        )
        .where(
            FoodItem.catalog_key == catalog_key,
            FoodItem.family_id.is_(None),
            FoodItem.food_kind == "ingredient",
        )
    )
    if item is None:
        raise SharedIngredientEnrichmentError(
            f"Shared ingredient {catalog_key!r} was not found."
        )
    return item


def _recipes_using_ingredient(
    db: Session,
    ingredient_id: uuid.UUID,
) -> list[Recipe]:
    return list(
        db.scalars(
            select(Recipe)
            .join(RecipeIngredient)
            .options(
                selectinload(Recipe.ingredients)
                .selectinload(RecipeIngredient.food_item)
                .selectinload(FoodItem.compositions)
                .selectinload(FoodCompositionSnapshot.nutrients),
                selectinload(Recipe.compositions),
            )
            .where(
                RecipeIngredient.food_item_id == ingredient_id,
                Recipe.is_active.is_(True),
            )
        )
        .unique()
        .all()
    )


def _notes_payload(composition: FoodCompositionSnapshot) -> dict[str, object]:
    if not composition.notes:
        return {}
    try:
        payload = json.loads(composition.notes)
    except json.JSONDecodeError:
        return {}
    return dict(payload) if isinstance(payload, dict) else {}


def _existing_portion_conversions(
    item: FoodItem,
    *,
    food: FdcFoodNutrition,
) -> dict[str, object]:
    if not item.compositions:
        return {}
    latest = item.compositions[-1]
    if latest.source_reference != food.source_reference:
        return {}
    raw = _notes_payload(latest).get("portion_conversions")
    return dict(raw) if isinstance(raw, dict) else {}


def _portion_conversion(
    food: FdcFoodNutrition,
    *,
    unit_portion: FdcFoodPortion,
    recipe_unit_quantity: Decimal | None,
) -> dict[str, object]:
    effective_quantity = _effective_recipe_unit_quantity(
        unit_portion,
        recipe_unit_quantity,
    )
    grams_per_recipe_unit = unit_portion.gram_weight / effective_quantity
    return {
        "reference_unit": "g",
        "quantity_in_reference_unit": str(grams_per_recipe_unit),
        "source": "usda-fdc",
        "source_reference": food.source_reference,
        "fdc_portion_id": unit_portion.portion_id,
        "fdc_portion_amount": str(unit_portion.amount),
        "fdc_portion_gram_weight": str(unit_portion.gram_weight),
        "fdc_portion_description": unit_portion.description,
        "fdc_measure_unit": unit_portion.measure_unit,
        "fdc_modifier": unit_portion.modifier,
        "recipe_unit_quantity": str(effective_quantity),
    }


def _composition_notes(
    food: FdcFoodNutrition,
    *,
    unit_portion: FdcFoodPortion | None,
    recipe_unit: str | None,
    recipe_unit_quantity: Decimal | None,
    existing_portion_conversions: dict[str, object],
) -> str:
    payload: dict[str, object] = {
        "fdc_id": food.fdc_id,
        "description": food.description,
        "data_type": food.data_type,
        "publication_date": food.publication_date,
        "reference_basis": "100 g edible portion",
        "curation": "explicitly-approved-match",
    }
    conversions = dict(existing_portion_conversions)
    if unit_portion is not None and recipe_unit is not None:
        conversions[recipe_unit] = _portion_conversion(
            food,
            unit_portion=unit_portion,
            recipe_unit_quantity=recipe_unit_quantity,
        )
    if conversions:
        payload["portion_conversions"] = conversions
    return json.dumps(payload, sort_keys=True)


def _conversion_data_version(
    composition: FoodCompositionSnapshot,
    *,
    food: FdcFoodNutrition,
    unit_portion: FdcFoodPortion,
    recipe_unit: str,
    recipe_unit_quantity: Decimal | None,
) -> str:
    effective_quantity = _effective_recipe_unit_quantity(
        unit_portion,
        recipe_unit_quantity,
    )
    evidence = (
        f"{composition.data_version}|{food.fdc_id}|{unit_portion.portion_id}|"
        f"{recipe_unit}|{effective_quantity}"
    )
    digest = hashlib.sha256(evidence.encode("utf-8")).hexdigest()[:12]
    return f"{composition.data_version[:49]}-c{digest}"[:64]


def apply_fdc_portion_conversion_to_shared_ingredient(
    db: Session,
    *,
    catalog_key: str,
    food: FdcFoodNutrition,
    unit_portion: FdcFoodPortion,
    recipe_unit: str,
    recipe_unit_quantity: Decimal | None = None,
    effective_at: datetime | None = None,
) -> SharedIngredientEnrichmentResult:
    if food.data_type not in GENERIC_DATA_TYPES:
        raise SharedIngredientEnrichmentError(
            f"FoodData Central data type {food.data_type!r} "
            "is not approved for generic ingredient conversions."
        )
    normalized_recipe_unit = _normalized_recipe_unit(recipe_unit)
    if normalized_recipe_unit is None:
        raise SharedIngredientEnrichmentError("recipe_unit must not be empty.")
    if recipe_unit_quantity is not None and recipe_unit_quantity <= 0:
        raise SharedIngredientEnrichmentError(
            "recipe_unit_quantity must be positive."
        )

    item = _shared_ingredient(db, catalog_key=catalog_key)
    if not item.compositions:
        raise SharedIngredientEnrichmentError(
            "A portion conversion requires an existing nutrition composition."
        )
    latest = item.compositions[-1]
    if latest.energy_kcal is None:
        raise SharedIngredientEnrichmentError(
            "A portion conversion requires an existing energy value."
        )

    payload = _notes_payload(latest)
    raw_conversions = payload.get("portion_conversions")
    conversions = dict(raw_conversions) if isinstance(raw_conversions, dict) else {}
    conversion = _portion_conversion(
        food,
        unit_portion=unit_portion,
        recipe_unit_quantity=recipe_unit_quantity,
    )
    if conversions.get(normalized_recipe_unit) == conversion:
        return SharedIngredientEnrichmentResult(
            ingredient_id=item.id,
            catalog_key=item.catalog_key,
            composition_id=latest.id,
            data_version=latest.data_version,
            created=False,
            recalculated_recipe_ids=(),
        )

    conversions[normalized_recipe_unit] = conversion
    payload["portion_conversions"] = conversions
    data_version = _conversion_data_version(
        latest,
        food=food,
        unit_portion=unit_portion,
        recipe_unit=normalized_recipe_unit,
        recipe_unit_quantity=recipe_unit_quantity,
    )
    composition = FoodCompositionSnapshot(
        reference_quantity=latest.reference_quantity,
        reference_unit=latest.reference_unit,
        energy_kcal=latest.energy_kcal,
        data_version=data_version,
        source=latest.source,
        source_reference=latest.source_reference,
        effective_at=effective_at or datetime.now(UTC),
        notes=json.dumps(payload, ensure_ascii=False, sort_keys=True),
    )
    composition.nutrients.extend(
        FoodNutrientComponent(
            nutrient_key=nutrient.nutrient_key,
            value=nutrient.value,
            unit=nutrient.unit,
        )
        for nutrient in latest.nutrients
    )
    item.compositions.append(composition)
    db.flush()

    recipes = _recipes_using_ingredient(db, item.id)
    for recipe in recipes:
        build_recipe_composition(recipe)
    db.flush()
    return SharedIngredientEnrichmentResult(
        ingredient_id=item.id,
        catalog_key=item.catalog_key,
        composition_id=composition.id,
        data_version=data_version,
        created=True,
        recalculated_recipe_ids=tuple(recipe.id for recipe in recipes),
    )


def apply_fdc_nutrition_to_shared_ingredient(
    db: Session,
    *,
    catalog_key: str,
    food: FdcFoodNutrition,
    effective_at: datetime | None = None,
    unit_portion: FdcFoodPortion | None = None,
    recipe_unit: str | None = None,
    recipe_unit_quantity: Decimal | None = None,
) -> SharedIngredientEnrichmentResult:
    if food.data_type not in GENERIC_DATA_TYPES:
        raise SharedIngredientEnrichmentError(
            f"FoodData Central data type {food.data_type!r} "
            "is not approved for generic ingredients."
        )
    if food.energy_kcal is None:
        raise SharedIngredientEnrichmentError(
            "Approved FoodData Central match does not contain kcal energy."
        )

    normalized_recipe_unit = _normalized_recipe_unit(recipe_unit)
    if (unit_portion is None) != (normalized_recipe_unit is None):
        raise SharedIngredientEnrichmentError(
            "A portion conversion requires both unit_portion and recipe_unit."
        )
    if recipe_unit_quantity is not None:
        if unit_portion is None:
            raise SharedIngredientEnrichmentError(
                "recipe_unit_quantity requires an approved unit_portion."
            )
        if recipe_unit_quantity <= 0:
            raise SharedIngredientEnrichmentError(
                "recipe_unit_quantity must be positive."
            )

    item = _shared_ingredient(db, catalog_key=catalog_key)
    data_version = _data_version(
        food,
        unit_portion=unit_portion,
        recipe_unit=normalized_recipe_unit,
        recipe_unit_quantity=recipe_unit_quantity,
    )
    existing = next(
        (
            composition
            for composition in item.compositions
            if composition.data_version == data_version
        ),
        None,
    )
    if existing is not None:
        return SharedIngredientEnrichmentResult(
            ingredient_id=item.id,
            catalog_key=item.catalog_key,
            composition_id=existing.id,
            data_version=data_version,
            created=False,
            recalculated_recipe_ids=(),
        )

    existing_conversions = _existing_portion_conversions(item, food=food)
    composition = FoodCompositionSnapshot(
        reference_quantity=100,
        reference_unit="g",
        energy_kcal=food.energy_kcal,
        data_version=data_version,
        source="usda-fdc",
        source_reference=food.source_reference,
        effective_at=effective_at or datetime.now(UTC),
        notes=_composition_notes(
            food,
            unit_portion=unit_portion,
            recipe_unit=normalized_recipe_unit,
            recipe_unit_quantity=recipe_unit_quantity,
            existing_portion_conversions=existing_conversions,
        ),
    )
    composition.nutrients.extend(
        FoodNutrientComponent(
            nutrient_key=nutrient.key,
            value=nutrient.value,
            unit=nutrient.unit,
        )
        for nutrient in food.nutrients
    )
    item.compositions.append(composition)
    db.flush()

    recipes = _recipes_using_ingredient(db, item.id)
    for recipe in recipes:
        build_recipe_composition(recipe)
    db.flush()

    return SharedIngredientEnrichmentResult(
        ingredient_id=item.id,
        catalog_key=item.catalog_key,
        composition_id=composition.id,
        data_version=data_version,
        created=True,
        recalculated_recipe_ids=tuple(recipe.id for recipe in recipes),
    )