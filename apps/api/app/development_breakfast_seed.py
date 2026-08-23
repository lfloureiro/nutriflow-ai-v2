import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import delete, select
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

BREAKFAST_NAMESPACE = uuid.UUID("c2438f32-cd97-41f9-9387-85227b437534")
BREAKFAST_SOURCE = "development-breakfast"
BREAKFAST_SOURCE_REFERENCE = "nutriflow-v2-shared-breakfast-estimates-v1"
BREAKFAST_CALCULATION_VERSION = "development-breakfast-estimate-v1"
BREAKFAST_DATA_VERSION = "breakfast-estimate-v1"
BREAKFAST_EFFECTIVE_AT = datetime(2026, 8, 23, 20, 0, tzinfo=UTC)


@dataclass(frozen=True)
class BreakfastIngredientDefinition:
    key: str
    name: str


@dataclass(frozen=True)
class BreakfastRecipeIngredientDefinition:
    ingredient_key: str
    quantity: Decimal
    unit: str


@dataclass(frozen=True)
class BreakfastRecipeDefinition:
    key: str
    name: str
    description: str
    energy_kcal: Decimal
    protein_g: Decimal
    fiber_g: Decimal
    sodium_mg: Decimal
    ingredients: tuple[BreakfastRecipeIngredientDefinition, ...]


@dataclass(frozen=True)
class DevelopmentBreakfastSeedResult:
    ingredient_count: int
    recipe_count: int


INGREDIENTS = (
    BreakfastIngredientDefinition("coffee", "Café"),
    BreakfastIngredientDefinition("milk", "Leite meio-gordo"),
    BreakfastIngredientDefinition("toast-bread", "Pão para torrada"),
    BreakfastIngredientDefinition("butter", "Manteiga"),
    BreakfastIngredientDefinition("breakfast-cereal", "Cereais de pequeno-almoço"),
    BreakfastIngredientDefinition("cerelac", "Cerelac"),
    BreakfastIngredientDefinition("natural-yogurt", "Iogurte natural"),
    BreakfastIngredientDefinition("greek-yogurt", "Iogurte grego"),
    BreakfastIngredientDefinition("muesli", "Muesli"),
    BreakfastIngredientDefinition("banana", "Banana"),
    BreakfastIngredientDefinition("berries", "Frutos vermelhos"),
    BreakfastIngredientDefinition("apple", "Maçã"),
    BreakfastIngredientDefinition("nestum", "Nestum"),
)


def _ri(key: str, quantity: str, unit: str) -> BreakfastRecipeIngredientDefinition:
    return BreakfastRecipeIngredientDefinition(key, Decimal(quantity), unit)


RECIPES = (
    BreakfastRecipeDefinition(
        "coffee-milk-butter-toast",
        "Café com leite e torrada com manteiga",
        "Café com leite e uma torrada com manteiga.",
        Decimal(285),
        Decimal(11),
        Decimal("2.5"),
        Decimal(330),
        (_ri("coffee", "60", "ml"), _ri("milk", "180", "ml"), _ri("toast-bread", "60", "g"), _ri("butter", "10", "g")),
    ),
    BreakfastRecipeDefinition(
        "cereal-milk",
        "Cereais com leite",
        "Taça de cereais de pequeno-almoço com leite.",
        Decimal(285),
        Decimal(10),
        Decimal(4),
        Decimal(260),
        (_ri("breakfast-cereal", "45", "g"), _ri("milk", "200", "ml")),
    ),
    BreakfastRecipeDefinition(
        "cerelac-milk",
        "Cerelac com leite",
        "Cerelac preparado com leite.",
        Decimal(305),
        Decimal(11),
        Decimal("2.5"),
        Decimal(210),
        (_ri("cerelac", "50", "g"), _ri("milk", "200", "ml")),
    ),
    BreakfastRecipeDefinition(
        "yogurt-muesli",
        "Iogurte com muesli",
        "Iogurte natural com muesli.",
        Decimal(280),
        Decimal(13),
        Decimal(5),
        Decimal(150),
        (_ri("natural-yogurt", "170", "g"), _ri("muesli", "45", "g")),
    ),
    BreakfastRecipeDefinition(
        "muesli-milk",
        "Muesli com leite",
        "Taça de muesli com leite.",
        Decimal(295),
        Decimal(11),
        Decimal(6),
        Decimal(155),
        (_ri("muesli", "50", "g"), _ri("milk", "200", "ml")),
    ),
    BreakfastRecipeDefinition(
        "yogurt-cereal",
        "Iogurte com cereais",
        "Iogurte natural com cereais de pequeno-almoço.",
        Decimal(235),
        Decimal(11),
        Decimal(3),
        Decimal(170),
        (_ri("natural-yogurt", "170", "g"), _ri("breakfast-cereal", "35", "g")),
    ),
    BreakfastRecipeDefinition(
        "yogurt-muesli-banana",
        "Iogurte, muesli e banana",
        "Iogurte natural com muesli e banana.",
        Decimal(365),
        Decimal(14),
        Decimal(8),
        Decimal(155),
        (_ri("natural-yogurt", "170", "g"), _ri("muesli", "40", "g"), _ri("banana", "100", "g")),
    ),
    BreakfastRecipeDefinition(
        "cereal-milk-banana",
        "Cereais, leite e banana",
        "Cereais com leite e banana.",
        Decimal(345),
        Decimal(11),
        Decimal(7),
        Decimal(250),
        (_ri("breakfast-cereal", "40", "g"), _ri("milk", "200", "ml"), _ri("banana", "100", "g")),
    ),
    BreakfastRecipeDefinition(
        "greek-yogurt-muesli-berries",
        "Iogurte grego, muesli e frutos vermelhos",
        "Iogurte grego com muesli e frutos vermelhos.",
        Decimal(330),
        Decimal(18),
        Decimal(7),
        Decimal(145),
        (_ri("greek-yogurt", "170", "g"), _ri("muesli", "40", "g"), _ri("berries", "100", "g")),
    ),
    BreakfastRecipeDefinition(
        "muesli-milk-apple",
        "Muesli, leite e maçã",
        "Muesli com leite e maçã.",
        Decimal(355),
        Decimal(11),
        Decimal(9),
        Decimal(155),
        (_ri("muesli", "50", "g"), _ri("milk", "200", "ml"), _ri("apple", "120", "g")),
    ),
    BreakfastRecipeDefinition(
        "nestum-milk",
        "Nestum com leite",
        "Nestum preparado com leite.",
        Decimal(260),
        Decimal(10),
        Decimal(4),
        Decimal(190),
        (_ri("nestum", "40", "g"), _ri("milk", "200", "ml")),
    ),
)


def _stable_id(kind: str, key: str) -> uuid.UUID:
    return uuid.uuid5(BREAKFAST_NAMESPACE, f"{kind}:{key}")


def _ensure_ingredient(session: Session, definition: BreakfastIngredientDefinition) -> FoodItem:
    item_id = _stable_id("ingredient", definition.key)
    catalog_key = f"breakfast:ingredient:{definition.key}"
    owner = session.scalar(select(FoodItem).where(FoodItem.catalog_key == catalog_key))
    if owner is not None and owner.id != item_id:
        raise ValueError(f"Breakfast ingredient key conflict: {catalog_key!r}.")
    item = session.get(FoodItem, item_id)
    if item is None:
        item = FoodItem(id=item_id)
        session.add(item)
    item.family_id = None
    item.catalog_key = catalog_key
    item.name = definition.name
    item.food_kind = "ingredient"
    item.source = BREAKFAST_SOURCE
    item.source_reference = BREAKFAST_SOURCE_REFERENCE
    item.is_active = True
    return item


def _ensure_recipe(
    session: Session,
    definition: BreakfastRecipeDefinition,
    ingredients: dict[str, FoodItem],
) -> Recipe:
    recipe_id = _stable_id("recipe", definition.key)
    recipe_key = f"breakfast:recipe:{definition.key}"
    owner = session.scalar(select(Recipe).where(Recipe.recipe_key == recipe_key))
    if owner is not None and owner.id != recipe_id:
        raise ValueError(f"Breakfast recipe key conflict: {recipe_key!r}.")
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
    recipe.source = BREAKFAST_SOURCE
    recipe.source_reference = BREAKFAST_SOURCE_REFERENCE
    recipe.is_active = True
    session.flush()

    session.execute(delete(RecipeIngredient).where(RecipeIngredient.recipe_id == recipe.id))
    session.flush()
    for index, ingredient_definition in enumerate(definition.ingredients):
        ingredient = ingredients[ingredient_definition.ingredient_key]
        session.add(
            RecipeIngredient(
                id=_stable_id("recipe-ingredient", f"{definition.key}:{index}"),
                recipe_id=recipe.id,
                food_item_id=ingredient.id,
                quantity=ingredient_definition.quantity,
                unit=ingredient_definition.unit,
                sort_order=index,
                notes="Porção de desenvolvimento para uma pessoa.",
            )
        )

    composition_id = _stable_id("composition", definition.key)
    composition = session.get(RecipeCompositionSnapshot, composition_id)
    if composition is None:
        composition = RecipeCompositionSnapshot(id=composition_id, recipe_id=recipe.id)
        session.add(composition)
    composition.recipe_id = recipe.id
    composition.reference_quantity = Decimal(1)
    composition.reference_unit = "serving"
    composition.energy_kcal = definition.energy_kcal
    composition.composition_version = BREAKFAST_DATA_VERSION
    composition.calculation_version = BREAKFAST_CALCULATION_VERSION
    composition.calculation_inputs = {
        "evidence_level": "estimated",
        "confidence": "medium",
        "purpose": "development breakfast catalogue",
        "warning": "Portions and nutrition are estimates, not manufacturer-specific values.",
    }
    composition.computed_at = BREAKFAST_EFFECTIVE_AT
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
    return recipe


def seed_development_breakfast_catalog(
    session: Session,
    *,
    families: tuple[Family, ...] = (),
) -> DevelopmentBreakfastSeedResult:
    ingredients = {
        definition.key: _ensure_ingredient(session, definition)
        for definition in INGREDIENTS
    }
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
            profile.planning_category = "breakfast"
            profile.primary_protein = None
            profile.suitable_meal_types = ["breakfast"]
            profile.auto_plan_enabled = True
            profile.source = BREAKFAST_SOURCE
            profile.source_reference = BREAKFAST_SOURCE_REFERENCE
    session.flush()

    return DevelopmentBreakfastSeedResult(
        ingredient_count=len(ingredients),
        recipe_count=len(recipes),
    )
