from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.food_catalog import FoodItem, Recipe, RecipeIngredient
from app.services.recipe_nutrition import (
    QUALITATIVE_UNITS,
    _latest_food_composition,
    _scale_recipe_ingredient,
)
from app.services.serving_nutrition import UnsupportedUnitConversionError

BLOCKER_MISSING_COMPOSITION = "MISSING_COMPOSITION"
BLOCKER_MISSING_ENERGY = "MISSING_ENERGY"
BLOCKER_MISSING_CONVERSION = "MISSING_CONVERSION"

STATUS_READY = "READY"
STATUS_BLOCKED = "BLOCKED"
STATUS_NO_INGREDIENTS = "NO_INGREDIENTS"


@dataclass(frozen=True)
class IngredientReadiness:
    recipe_name: str
    catalog_key: str
    ingredient_name: str
    quantity: Decimal
    unit: str
    reference_unit: str | None
    qualitative: bool
    estimated_conversion: bool
    blockers: tuple[str, ...]

    @property
    def blocking(self) -> bool:
        return bool(self.blockers)


@dataclass(frozen=True)
class RecipeReadinessDiagnostic:
    recipe_name: str
    ingredient_count: int
    quantitative_count: int
    qualitative_count: int
    ready_quantitative_count: int
    estimated_conversion_count: int
    missing_composition_count: int
    missing_energy_count: int
    missing_conversion_count: int
    blocker_count: int
    status: str
    ingredients: tuple[IngredientReadiness, ...]

    @property
    def energy_calculable(self) -> bool:
        return self.status == STATUS_READY


@dataclass(frozen=True)
class IngredientBlockerPriority:
    blocker_type: str
    catalog_key: str
    ingredient_name: str
    recipe_unit: str | None
    reference_unit: str | None
    affected_recipe_count: int
    occurrence_count: int
    sole_blocker_recipe_count: int


@dataclass(frozen=True)
class IngredientReadinessReport:
    recipes: tuple[RecipeReadinessDiagnostic, ...]
    priorities: tuple[IngredientBlockerPriority, ...]

    @property
    def ready_recipe_count(self) -> int:
        return sum(item.energy_calculable for item in self.recipes)

    @property
    def blocked_recipe_count(self) -> int:
        return sum(item.status == STATUS_BLOCKED for item in self.recipes)

    @property
    def no_ingredients_recipe_count(self) -> int:
        return sum(item.status == STATUS_NO_INGREDIENTS for item in self.recipes)


def _blocker_key(item: IngredientReadiness, blocker: str) -> tuple[str, str, str | None, str | None]:
    if blocker == BLOCKER_MISSING_CONVERSION:
        return (
            blocker,
            item.catalog_key,
            item.unit.strip().casefold(),
            item.reference_unit,
        )
    return (blocker, item.catalog_key, None, item.reference_unit)


def inspect_recipe_ingredient(
    recipe: Recipe,
    ingredient: RecipeIngredient,
) -> IngredientReadiness:
    normalized_unit = ingredient.unit.strip().casefold()
    qualitative = normalized_unit in QUALITATIVE_UNITS
    composition = _latest_food_composition(ingredient)

    if qualitative:
        return IngredientReadiness(
            recipe_name=recipe.name,
            catalog_key=ingredient.food_item.catalog_key,
            ingredient_name=ingredient.food_item.name,
            quantity=ingredient.quantity,
            unit=normalized_unit,
            reference_unit=composition.reference_unit if composition is not None else None,
            qualitative=True,
            estimated_conversion=False,
            blockers=(),
        )

    if composition is None:
        return IngredientReadiness(
            recipe_name=recipe.name,
            catalog_key=ingredient.food_item.catalog_key,
            ingredient_name=ingredient.food_item.name,
            quantity=ingredient.quantity,
            unit=normalized_unit,
            reference_unit=None,
            qualitative=False,
            estimated_conversion=False,
            blockers=(BLOCKER_MISSING_COMPOSITION,),
        )

    blockers: list[str] = []
    if composition.energy_kcal is None:
        blockers.append(BLOCKER_MISSING_ENERGY)

    estimated_conversion = False
    try:
        _, conversion = _scale_recipe_ingredient(recipe, ingredient, composition)
        estimated_conversion = conversion is not None and conversion.estimated
    except UnsupportedUnitConversionError:
        blockers.append(BLOCKER_MISSING_CONVERSION)

    return IngredientReadiness(
        recipe_name=recipe.name,
        catalog_key=ingredient.food_item.catalog_key,
        ingredient_name=ingredient.food_item.name,
        quantity=ingredient.quantity,
        unit=normalized_unit,
        reference_unit=composition.reference_unit.strip().casefold(),
        qualitative=False,
        estimated_conversion=estimated_conversion,
        blockers=tuple(blockers),
    )


def _recipe_diagnostic(recipe: Recipe) -> RecipeReadinessDiagnostic:
    inspected = tuple(
        inspect_recipe_ingredient(recipe, ingredient) for ingredient in recipe.ingredients
    )
    quantitative = tuple(item for item in inspected if not item.qualitative)
    qualitative = tuple(item for item in inspected if item.qualitative)
    ready_quantitative = tuple(item for item in quantitative if not item.blocking)

    missing_composition_count = sum(
        BLOCKER_MISSING_COMPOSITION in item.blockers for item in quantitative
    )
    missing_energy_count = sum(
        BLOCKER_MISSING_ENERGY in item.blockers for item in quantitative
    )
    missing_conversion_count = sum(
        BLOCKER_MISSING_CONVERSION in item.blockers for item in quantitative
    )
    blocker_count = sum(len(item.blockers) for item in quantitative)

    if not inspected:
        status = STATUS_NO_INGREDIENTS
    elif quantitative and blocker_count == 0:
        status = STATUS_READY
    else:
        status = STATUS_BLOCKED

    return RecipeReadinessDiagnostic(
        recipe_name=recipe.name,
        ingredient_count=len(inspected),
        quantitative_count=len(quantitative),
        qualitative_count=len(qualitative),
        ready_quantitative_count=len(ready_quantitative),
        estimated_conversion_count=sum(
            item.estimated_conversion for item in quantitative
        ),
        missing_composition_count=missing_composition_count,
        missing_energy_count=missing_energy_count,
        missing_conversion_count=missing_conversion_count,
        blocker_count=blocker_count,
        status=status,
        ingredients=inspected,
    )


def _priority_rows(
    diagnostics: tuple[RecipeReadinessDiagnostic, ...],
) -> tuple[IngredientBlockerPriority, ...]:
    occurrence_counts: dict[tuple[str, str, str | None, str | None], int] = defaultdict(int)
    affected_recipes: dict[
        tuple[str, str, str | None, str | None], set[str]
    ] = defaultdict(set)
    sole_blocker_recipes: dict[
        tuple[str, str, str | None, str | None], set[str]
    ] = defaultdict(set)
    labels: dict[
        tuple[str, str, str | None, str | None], tuple[str, str]
    ] = {}

    for recipe in diagnostics:
        recipe_keys: set[tuple[str, str, str | None, str | None]] = set()
        for item in recipe.ingredients:
            for blocker in item.blockers:
                key = _blocker_key(item, blocker)
                labels[key] = (item.catalog_key, item.ingredient_name)
                occurrence_counts[key] += 1
                affected_recipes[key].add(recipe.recipe_name)
                recipe_keys.add(key)
        if len(recipe_keys) == 1:
            sole_key = next(iter(recipe_keys))
            sole_blocker_recipes[sole_key].add(recipe.recipe_name)

    rows = [
        IngredientBlockerPriority(
            blocker_type=key[0],
            catalog_key=labels[key][0],
            ingredient_name=labels[key][1],
            recipe_unit=key[2],
            reference_unit=key[3],
            affected_recipe_count=len(affected_recipes[key]),
            occurrence_count=occurrence_counts[key],
            sole_blocker_recipe_count=len(sole_blocker_recipes[key]),
        )
        for key in occurrence_counts
    ]
    return tuple(
        sorted(
            rows,
            key=lambda item: (
                item.sole_blocker_recipe_count,
                item.affected_recipe_count,
                item.occurrence_count,
                item.ingredient_name.casefold(),
            ),
            reverse=True,
        )
    )


def analyze_ingredient_readiness(
    recipes: list[Recipe] | tuple[Recipe, ...],
) -> IngredientReadinessReport:
    diagnostics = tuple(_recipe_diagnostic(recipe) for recipe in recipes)
    return IngredientReadinessReport(
        recipes=diagnostics,
        priorities=_priority_rows(diagnostics),
    )


def load_legacy_recipes_for_readiness(
    db: Session,
    *,
    recipe_key_prefix: str = "legacy-v1:",
) -> list[Recipe]:
    statement = (
        select(Recipe)
        .options(
            selectinload(Recipe.ingredients)
            .selectinload(RecipeIngredient.food_item)
            .selectinload(FoodItem.compositions)
        )
        .where(
            Recipe.is_active.is_(True),
            Recipe.recipe_key.like(f"{recipe_key_prefix}%"),
        )
        .order_by(Recipe.name)
    )
    return list(db.scalars(statement))


def build_ingredient_readiness_report(
    db: Session,
    *,
    recipe_key_prefix: str = "legacy-v1:",
) -> IngredientReadinessReport:
    recipes = load_legacy_recipes_for_readiness(
        db,
        recipe_key_prefix=recipe_key_prefix,
    )
    return analyze_ingredient_readiness(recipes)
