import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

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
from app.models.meal_candidate_planning_profile import MealCandidatePlanningProfile

SNACK_NAMESPACE = uuid.UUID("5d263c8a-e632-4fdb-ad92-c8bf3306235f")
SNACK_SOURCE = "development-snack"
SNACK_SOURCE_REFERENCE = "nutriflow-v2-shared-snack-estimates-v1"
SNACK_CALCULATION_VERSION = "development-snack-estimate-v1"
SNACK_DATA_VERSION = "snack-estimate-v1"
SNACK_EFFECTIVE_AT = datetime(2026, 8, 23, 20, 30, tzinfo=UTC)


@dataclass(frozen=True)
class SnackIngredientDefinition:
    key: str
    name: str


@dataclass(frozen=True)
class SnackRecipeIngredientDefinition:
    ingredient_key: str
    quantity: Decimal
    unit: str


@dataclass(frozen=True)
class SnackRecipeDefinition:
    key: str
    name: str
    description: str
    energy_kcal: Decimal
    protein_g: Decimal
    fiber_g: Decimal
    sodium_mg: Decimal
    ingredients: tuple[SnackRecipeIngredientDefinition, ...]


@dataclass(frozen=True)
class DevelopmentSnackSeedResult:
    new_ingredient_count: int
    recipe_count: int


SHARED_BREAKFAST_INGREDIENT_KEYS = {
    "milk": "breakfast:ingredient:milk",
    "toast-bread": "breakfast:ingredient:toast-bread",
    "natural-yogurt": "breakfast:ingredient:natural-yogurt",
    "greek-yogurt": "breakfast:ingredient:greek-yogurt",
    "muesli": "breakfast:ingredient:muesli",
    "breakfast-cereal": "breakfast:ingredient:breakfast-cereal",
    "banana": "breakfast:ingredient:banana",
    "berries": "breakfast:ingredient:berries",
    "apple": "breakfast:ingredient:apple",
}

NEW_INGREDIENTS = (
    SnackIngredientDefinition("mixed-nuts", "Frutos secos"),
    SnackIngredientDefinition("cheese", "Queijo fatiado"),
    SnackIngredientDefinition("ham", "Fiambre fatiado"),
    SnackIngredientDefinition("oat-biscuits", "Bolachas de aveia"),
)


def _ri(key: str, quantity: str, unit: str) -> SnackRecipeIngredientDefinition:
    return SnackRecipeIngredientDefinition(key, Decimal(quantity), unit)


RECIPES = (
    SnackRecipeDefinition(
        "yogurt-banana",
        "Iogurte natural com banana",
        "Iogurte natural com banana.",
        Decimal(200),
        Decimal(9),
        Decimal(3),
        Decimal(110),
        (_ri("natural-yogurt", "170", "g"), _ri("banana", "90", "g")),
    ),
    SnackRecipeDefinition(
        "small-yogurt-muesli",
        "Iogurte com muesli, dose pequena",
        "Iogurte natural com uma dose pequena de muesli.",
        Decimal(220),
        Decimal(11),
        Decimal(4),
        Decimal(125),
        (_ri("natural-yogurt", "150", "g"), _ri("muesli", "30", "g")),
    ),
    SnackRecipeDefinition(
        "small-yogurt-cereal",
        "Iogurte com cereais, dose pequena",
        "Iogurte natural com uma dose pequena de cereais.",
        Decimal(205),
        Decimal(9),
        Decimal(2),
        Decimal(150),
        (
            _ri("natural-yogurt", "150", "g"),
            _ri("breakfast-cereal", "25", "g"),
        ),
    ),
    SnackRecipeDefinition(
        "greek-yogurt-berries",
        "Iogurte grego com frutos vermelhos",
        "Iogurte grego com frutos vermelhos.",
        Decimal(190),
        Decimal(15),
        Decimal(4),
        Decimal(85),
        (_ri("greek-yogurt", "150", "g"), _ri("berries", "100", "g")),
    ),
    SnackRecipeDefinition(
        "small-muesli-milk",
        "Muesli com leite, dose pequena",
        "Dose pequena de muesli com leite.",
        Decimal(235),
        Decimal(9),
        Decimal(5),
        Decimal(125),
        (_ri("muesli", "35", "g"), _ri("milk", "180", "ml")),
    ),
    SnackRecipeDefinition(
        "small-cereal-milk",
        "Cereais com leite, dose pequena",
        "Dose pequena de cereais com leite.",
        Decimal(225),
        Decimal(8),
        Decimal(3),
        Decimal(215),
        (_ri("breakfast-cereal", "30", "g"), _ri("milk", "180", "ml")),
    ),
    SnackRecipeDefinition(
        "apple-nuts",
        "Maçã e frutos secos",
        "Maçã com uma pequena porção de frutos secos.",
        Decimal(215),
        Decimal(5),
        Decimal(6),
        Decimal(5),
        (_ri("apple", "150", "g"), _ri("mixed-nuts", "25", "g")),
    ),
    SnackRecipeDefinition(
        "banana-nuts",
        "Banana e frutos secos",
        "Banana com uma pequena porção de frutos secos.",
        Decimal(250),
        Decimal(6),
        Decimal(5),
        Decimal(5),
        (_ri("banana", "120", "g"), _ri("mixed-nuts", "25", "g")),
    ),
    SnackRecipeDefinition(
        "cheese-toast",
        "Torrada com queijo",
        "Torrada com queijo fatiado.",
        Decimal(245),
        Decimal(12),
        Decimal(3),
        Decimal(480),
        (_ri("toast-bread", "55", "g"), _ri("cheese", "30", "g")),
    ),
    SnackRecipeDefinition(
        "ham-cheese-toast",
        "Torrada mista",
        "Torrada com fiambre e queijo.",
        Decimal(290),
        Decimal(18),
        Decimal(3),
        Decimal(760),
        (
            _ri("toast-bread", "60", "g"),
            _ri("ham", "30", "g"),
            _ri("cheese", "30", "g"),
        ),
    ),
    SnackRecipeDefinition(
        "oat-biscuits-milk",
        "Bolachas de aveia e leite",
        "Bolachas de aveia acompanhadas com leite.",
        Decimal(260),
        Decimal(9),
        Decimal(4),
        Decimal(220),
        (_ri("oat-biscuits", "40", "g"), _ri("milk", "180", "ml")),
    ),
    SnackRecipeDefinition(
        "yogurt-apple-muesli",
        "Iogurte, maçã e muesli",
        "Iogurte natural com maçã e uma pequena dose de muesli.",
        Decimal(265),
        Decimal(11),
        Decimal(6),
        Decimal(120),
        (
            _ri("natural-yogurt", "150", "g"),
            _ri("apple", "100", "g"),
            _ri("muesli", "25", "g"),
        ),
    ),
)


def _stable_id(kind: str, key: str) -> uuid.UUID:
    return uuid.uuid5(SNACK_NAMESPACE, f"{kind}:{key}")


def _load_shared_ingredients(session: Session) -> dict[str, FoodItem]:
    result: dict[str, FoodItem] = {}
    for key, catalog_key in SHARED_BREAKFAST_INGREDIENT_KEYS.items():
        item = session.scalar(select(FoodItem).where(FoodItem.catalog_key == catalog_key))
        if item is None:
            raise RuntimeError(
                f"Shared snack catalogue requires breakfast ingredient {catalog_key!r}."
            )
        result[key] = item
    return result


def _ensure_new_ingredient(
    session: Session,
    definition: SnackIngredientDefinition,
) -> FoodItem:
    item_id = _stable_id("ingredient", definition.key)
    catalog_key = f"snack:ingredient:{definition.key}"
    owner = session.scalar(select(FoodItem).where(FoodItem.catalog_key == catalog_key))
    if owner is not None and owner.id != item_id:
        raise ValueError(f"Snack ingredient key conflict: {catalog_key!r}.")
    item = session.get(FoodItem, item_id)
    if item is None:
        item = FoodItem(id=item_id)
        session.add(item)
    item.family_id = None
    item.catalog_key = catalog_key
    item.name = definition.name
    item.food_kind = "ingredient"
    item.source = SNACK_SOURCE
    item.source_reference = SNACK_SOURCE_REFERENCE
    item.is_active = True
    return item


def _ensure_recipe_ingredients(
    session: Session,
    recipe: Recipe,
    definition: SnackRecipeDefinition,
    ingredients: dict[str, FoodItem],
) -> None:
    desired_ids = {
        _stable_id("recipe-ingredient", f"{definition.key}:{index}")
        for index in range(len(definition.ingredients))
    }
    existing_rows = list(
        session.scalars(
            select(RecipeIngredient).where(RecipeIngredient.recipe_id == recipe.id)
        ).all()
    )
    existing_by_id = {row.id: row for row in existing_rows}
    for row in existing_rows:
        if row.id not in desired_ids:
            session.delete(row)

    for index, ingredient_definition in enumerate(definition.ingredients):
        row_id = _stable_id("recipe-ingredient", f"{definition.key}:{index}")
        row = existing_by_id.get(row_id)
        if row is None:
            row = RecipeIngredient(id=row_id)
            session.add(row)
        ingredient = ingredients[ingredient_definition.ingredient_key]
        row.recipe_id = recipe.id
        row.food_item_id = ingredient.id
        row.quantity = ingredient_definition.quantity
        row.unit = ingredient_definition.unit
        row.preparation = None
        row.sort_order = index
        row.notes = "Porção de desenvolvimento para uma pessoa."
    session.flush()


def _ensure_recipe(
    session: Session,
    definition: SnackRecipeDefinition,
    ingredients: dict[str, FoodItem],
) -> Recipe:
    recipe_id = _stable_id("recipe", definition.key)
    recipe_key = f"snack:recipe:{definition.key}"
    owner = session.scalar(select(Recipe).where(Recipe.recipe_key == recipe_key))
    if owner is not None and owner.id != recipe_id:
        raise ValueError(f"Snack recipe key conflict: {recipe_key!r}.")
    recipe = session.get(Recipe, recipe_id)
    if recipe is None:
        recipe = Recipe(id=recipe_id)
        session.add(recipe)
    recipe.family_id = None
    recipe.recipe_key = recipe_key
    recipe.name = definition.name
    recipe.description = definition.description
    recipe.yield_quantity = None
    recipe.yield_unit = None
    recipe.serving_count = Decimal(1)
    recipe.source = SNACK_SOURCE
    recipe.source_reference = SNACK_SOURCE_REFERENCE
    recipe.is_active = True
    session.flush()

    _ensure_recipe_ingredients(session, recipe, definition, ingredients)

    composition_id = _stable_id("composition", definition.key)
    composition = session.get(RecipeCompositionSnapshot, composition_id)
    if composition is None:
        composition = RecipeCompositionSnapshot(id=composition_id, recipe_id=recipe.id)
        session.add(composition)
    composition.recipe_id = recipe.id
    composition.reference_quantity = Decimal(1)
    composition.reference_unit = "serving"
    composition.energy_kcal = definition.energy_kcal
    composition.composition_version = SNACK_DATA_VERSION
    composition.calculation_version = SNACK_CALCULATION_VERSION
    composition.calculation_inputs = {
        "evidence_level": "estimated",
        "confidence": "medium",
        "purpose": "development snack catalogue",
        "warning": "Portions and nutrition are estimates, not manufacturer-specific values.",
    }
    composition.computed_at = SNACK_EFFECTIVE_AT
    session.flush()

    values = {
        "protein": (definition.protein_g, "g"),
        "fiber": (definition.fiber_g, "g"),
        "sodium": (definition.sodium_mg, "mg"),
    }
    existing = {component.nutrient_key: component for component in composition.nutrients}
    for nutrient_key, (value, unit) in values.items():
        component = existing.get(nutrient_key)
        if component is None:
            component = RecipeNutrientComponent(
                id=_stable_id("nutrient", f"{definition.key}:{nutrient_key}"),
                composition_snapshot_id=composition.id,
                nutrient_key=nutrient_key,
                value=value,
                unit=unit,
            )
            session.add(component)
        else:
            component.value = value
            component.unit = unit
    session.flush()
    return recipe


def seed_development_snack_catalog(
    session: Session,
    *,
    families: tuple[Family, ...] = (),
) -> DevelopmentSnackSeedResult:
    ingredients = _load_shared_ingredients(session)
    for definition in NEW_INGREDIENTS:
        ingredients[definition.key] = _ensure_new_ingredient(session, definition)
    session.flush()

    recipes = {
        definition.key: _ensure_recipe(session, definition, ingredients)
        for definition in RECIPES
    }
    session.flush()

    for family in families:
        for definition in RECIPES:
            recipe = recipes[definition.key]
            profile_id = _stable_id("planning-profile", f"{family.id}:{definition.key}")
            profile = session.get(MealCandidatePlanningProfile, profile_id)
            if profile is None:
                profile = MealCandidatePlanningProfile(id=profile_id, family_id=family.id)
                session.add(profile)
            profile.family_id = family.id
            profile.candidate_kind = "recipe"
            profile.food_item_id = None
            profile.recipe_id = recipe.id
            profile.planning_category = "snack"
            profile.primary_protein = None
            profile.suitable_meal_types = ["snack"]
            profile.auto_plan_enabled = True
            profile.source = SNACK_SOURCE
            profile.source_reference = SNACK_SOURCE_REFERENCE
    session.flush()

    return DevelopmentSnackSeedResult(
        new_ingredient_count=len(NEW_INGREDIENTS),
        recipe_count=len(recipes),
    )
