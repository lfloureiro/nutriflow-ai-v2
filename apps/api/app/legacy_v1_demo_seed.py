import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import TypedDict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.family import Family
from app.models.food_catalog import (
    FoodItem,
    Recipe,
    RecipeCompositionSnapshot,
    RecipeIngredient,
    RecipeNutrientComponent,
)

LEGACY_V1_SOURCE = "legacy-v1-demo"
LEGACY_V1_SOURCE_REFERENCE = "nutriflow-ai:v1:demo_3_familias_20_receitas"
LEGACY_V1_DATA_VERSION = "legacy-v1-demo-v2"
LEGACY_V1_NAMESPACE = uuid.UUID("4f99ec16-c0a4-4b65-b118-2ca0a6f34967")
LEGACY_V1_SNAPSHOT_AT = datetime(2026, 4, 18, 12, 0, tzinfo=UTC)
LEGACY_V1_FIXTURE = (
    Path(__file__).resolve().parents[3] / "database" / "legacy-v1" / "demo_catalog_subset.json"
)
SYNTHETIC_NUTRITION_NOTE = (
    "Development-only synthetic nutrition estimate; recipe structure comes from v1, "
    "nutrition does not."
)


class _IngredientJson(TypedDict):
    id: int
    name: str


class _RecipeIngredientJson(TypedDict):
    ingredient_id: int
    quantity: str
    unit: str


class _RecipeJson(TypedDict):
    id: int
    name: str
    description: str
    serving_count: str
    ingredients: list[_RecipeIngredientJson]


class _FixtureJson(TypedDict):
    ingredients: list[_IngredientJson]
    recipes: list[_RecipeJson]


@dataclass(frozen=True)
class DemoRecipeNutrition:
    energy_kcal: Decimal
    protein_g: Decimal
    fiber_g: Decimal
    sodium_mg: Decimal


@dataclass(frozen=True)
class LegacyV1DemoSeedResult:
    ingredient_count: int
    recipe_count: int


class LegacyV1DemoSeedConflictError(ValueError):
    pass


LEGACY_V1_DEMO_NUTRITION = {
    1: DemoRecipeNutrition(
        energy_kcal=Decimal(2400),
        protein_g=Decimal(128),
        fiber_g=Decimal(28),
        sodium_mg=Decimal(2400),
    ),
    2: DemoRecipeNutrition(
        energy_kcal=Decimal(2520),
        protein_g=Decimal(132),
        fiber_g=Decimal(36),
        sodium_mg=Decimal(2600),
    ),
    3: DemoRecipeNutrition(
        energy_kcal=Decimal(2360),
        protein_g=Decimal(136),
        fiber_g=Decimal(20),
        sodium_mg=Decimal(2200),
    ),
    5: DemoRecipeNutrition(
        energy_kcal=Decimal(2240),
        protein_g=Decimal(144),
        fiber_g=Decimal(24),
        sodium_mg=Decimal(1800),
    ),
    6: DemoRecipeNutrition(
        energy_kcal=Decimal(2280),
        protein_g=Decimal(124),
        fiber_g=Decimal(22),
        sodium_mg=Decimal(2000),
    ),
}


def _fixture() -> _FixtureJson:
    with LEGACY_V1_FIXTURE.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    return _FixtureJson(
        ingredients=payload["ingredients"],
        recipes=payload["recipes"],
    )


def _stable_id(kind: str, legacy_id: int) -> uuid.UUID:
    return uuid.uuid5(LEGACY_V1_NAMESPACE, f"{kind}:{legacy_id}")


def _ingredient_key(legacy_id: int) -> str:
    return f"legacy-v1:ingredient:{legacy_id}"


def _recipe_key(legacy_id: int) -> str:
    return f"legacy-v1:recipe:{legacy_id}"


def _ensure_catalog_key_available(
    session: Session,
    *,
    catalog_key: str,
    expected_id: uuid.UUID,
) -> None:
    owner = session.scalar(select(FoodItem).where(FoodItem.catalog_key == catalog_key))
    if owner is not None and owner.id != expected_id:
        raise LegacyV1DemoSeedConflictError(
            f"Catalogue key {catalog_key!r} already belongs to another FoodItem."
        )


def _ensure_recipe_key_available(
    session: Session,
    *,
    recipe_key: str,
    expected_id: uuid.UUID,
) -> None:
    owner = session.scalar(select(Recipe).where(Recipe.recipe_key == recipe_key))
    if owner is not None and owner.id != expected_id:
        raise LegacyV1DemoSeedConflictError(
            f"Recipe key {recipe_key!r} already belongs to another Recipe."
        )


def _ensure_ingredient(
    session: Session,
    definition: _IngredientJson,
) -> FoodItem:
    legacy_id = definition["id"]
    item_id = _stable_id("ingredient", legacy_id)
    catalog_key = _ingredient_key(legacy_id)
    _ensure_catalog_key_available(
        session,
        catalog_key=catalog_key,
        expected_id=item_id,
    )

    item = session.get(FoodItem, item_id)
    if item is None:
        item = FoodItem(
            id=item_id,
            family=None,
            catalog_key=catalog_key,
            name=definition["name"],
            food_kind="ingredient",
            source=LEGACY_V1_SOURCE,
            source_reference=LEGACY_V1_SOURCE_REFERENCE,
            is_active=True,
        )
        session.add(item)
    else:
        item.family_id = None
        item.catalog_key = catalog_key
        item.name = definition["name"]
        item.food_kind = "ingredient"
        item.source = LEGACY_V1_SOURCE
        item.source_reference = LEGACY_V1_SOURCE_REFERENCE
        item.is_active = True
    return item


def _ensure_demo_composition(
    session: Session,
    recipe: Recipe,
    *,
    legacy_id: int,
    serving_count: Decimal,
) -> None:
    nutrition = LEGACY_V1_DEMO_NUTRITION[legacy_id]
    composition_id = _stable_id("recipe-composition", legacy_id)
    composition = session.get(RecipeCompositionSnapshot, composition_id)
    if composition is None:
        composition = RecipeCompositionSnapshot(
            id=composition_id,
            reference_quantity=serving_count,
            reference_unit="serving",
            energy_kcal=nutrition.energy_kcal,
            composition_version=LEGACY_V1_DATA_VERSION,
            calculation_version="legacy-v1-demo-synthetic-nutrition-v1",
            calculation_inputs={
                "recipe_source": LEGACY_V1_SOURCE_REFERENCE,
                "nutrition_source": "synthetic-development-fixture",
                "issues": [SYNTHETIC_NUTRITION_NOTE],
            },
            computed_at=LEGACY_V1_SNAPSHOT_AT,
        )
        recipe.compositions.append(composition)
    else:
        composition.recipe_id = recipe.id
        composition.reference_quantity = serving_count
        composition.reference_unit = "serving"
        composition.energy_kcal = nutrition.energy_kcal
        composition.composition_version = LEGACY_V1_DATA_VERSION
        composition.calculation_version = "legacy-v1-demo-synthetic-nutrition-v1"
        composition.calculation_inputs = {
            "recipe_source": LEGACY_V1_SOURCE_REFERENCE,
            "nutrition_source": "synthetic-development-fixture",
            "issues": [SYNTHETIC_NUTRITION_NOTE],
        }
        composition.computed_at = LEGACY_V1_SNAPSHOT_AT

    nutrient_values = {
        "protein": (nutrition.protein_g, "g"),
        "fiber": (nutrition.fiber_g, "g"),
        "sodium": (nutrition.sodium_mg, "mg"),
    }
    existing = {nutrient.nutrient_key: nutrient for nutrient in composition.nutrients}
    for index, (nutrient_key, (value, unit)) in enumerate(nutrient_values.items(), start=1):
        nutrient = existing.get(nutrient_key)
        if nutrient is None:
            nutrient = RecipeNutrientComponent(
                id=_stable_id("recipe-nutrient", legacy_id * 10 + index),
                nutrient_key=nutrient_key,
                value=value,
                unit=unit,
            )
            composition.nutrients.append(nutrient)
        else:
            nutrient.value = value
            nutrient.unit = unit


def _ensure_recipe(
    session: Session,
    definition: _RecipeJson,
    ingredients_by_legacy_id: dict[int, FoodItem],
) -> Recipe:
    legacy_id = definition["id"]
    recipe_id = _stable_id("recipe", legacy_id)
    recipe_key = _recipe_key(legacy_id)
    _ensure_recipe_key_available(
        session,
        recipe_key=recipe_key,
        expected_id=recipe_id,
    )

    serving_count = Decimal(definition["serving_count"])
    recipe = session.get(Recipe, recipe_id)
    if recipe is None:
        recipe = Recipe(
            id=recipe_id,
            family=None,
            recipe_key=recipe_key,
            name=definition["name"],
            description=definition["description"],
            serving_count=serving_count,
            source=LEGACY_V1_SOURCE,
            source_reference=LEGACY_V1_SOURCE_REFERENCE,
            is_active=True,
        )
        session.add(recipe)
        session.flush()
    else:
        recipe.family_id = None
        recipe.recipe_key = recipe_key
        recipe.name = definition["name"]
        recipe.description = definition["description"]
        recipe.serving_count = serving_count
        recipe.source = LEGACY_V1_SOURCE
        recipe.source_reference = LEGACY_V1_SOURCE_REFERENCE
        recipe.is_active = True

    if not recipe.ingredients:
        for index, ingredient_definition in enumerate(definition["ingredients"]):
            ingredient = ingredients_by_legacy_id[ingredient_definition["ingredient_id"]]
            recipe.ingredients.append(
                RecipeIngredient(
                    id=_stable_id("recipe-ingredient", legacy_id * 100 + index),
                    food_item=ingredient,
                    quantity=Decimal(ingredient_definition["quantity"]),
                    unit=ingredient_definition["unit"].lower(),
                    sort_order=index,
                    notes="Imported from the NutriFlow v1 demo snapshot.",
                )
            )

    _ensure_demo_composition(
        session,
        recipe,
        legacy_id=legacy_id,
        serving_count=serving_count,
    )
    return recipe


def seed_legacy_v1_demo_catalog(
    session: Session,
    *,
    family: Family,
    now: datetime | None = None,
) -> LegacyV1DemoSeedResult:
    instant = now or datetime.now(UTC)
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise ValueError("Legacy v1 demo seed instant must be timezone-aware.")
    _ = family

    fixture = _fixture()
    ingredients = {
        definition["id"]: _ensure_ingredient(session, definition)
        for definition in fixture["ingredients"]
    }
    session.flush()

    for definition in fixture["recipes"]:
        _ensure_recipe(session, definition, ingredients)
    session.flush()

    return LegacyV1DemoSeedResult(
        ingredient_count=len(fixture["ingredients"]),
        recipe_count=len(fixture["recipes"]),
    )
