from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.food_catalog import Recipe, RecipeIngredient
from app.services.nutrition_learning import normalize_food_text

DIM_PROTEIN = "protein"
DIM_CARBOHYDRATE = "carbohydrate"
DIM_VEGETABLE = "vegetable"
DIM_ENERGY_MODIFIER = "energy_modifier"
DIM_ACCESSORY = "accessory"
DIM_OTHER = "other"

COOKING_FRIED = "fried"
COOKING_AIR_FRIED = "air_fried"
COOKING_GRILLED = "grilled"
COOKING_BAKED = "baked"
COOKING_STEWED = "stewed"
COOKING_BOILED = "boiled"
COOKING_SAUTEED = "sauteed"
COOKING_UNKNOWN = "unknown"

_PROTEIN_ROOTS = (
    "frang",
    "peru",
    "bacalhau",
    "salmao",
    "pescad",
    "peix",
    "atum",
    "sardin",
    "carne",
    "vaca",
    "porco",
    "porc",
    "bife",
    "bifana",
    "almondeg",
    "hamburg",
    "coelho",
    "ovo",
    "camarao",
    "marisco",
    "polvo",
    "lula",
    "tofu",
    "seitan",
)
_LEGUME_ROOTS = ("grao", "feijao", "lentilh", "ervilh")
_CARB_ROOTS = (
    "arroz",
    "massa",
    "esparguet",
    "tagliatelle",
    "batata",
    "pao",
    "cuscuz",
    "couscous",
    "quinoa",
    "tortilha",
    "noodle",
)
_VEGETABLE_ROOTS = (
    "cebola",
    "tomate",
    "cenoura",
    "curgete",
    "abobor",
    "beringel",
    "brocol",
    "couve",
    "espinafre",
    "pimento",
    "cogumel",
    "legume",
    "salada",
)
_ENERGY_MODIFIER_ROOTS = (
    "azeite",
    "oleo",
    "manteig",
    "margarin",
    "natas",
    "maiones",
    "queijo",
    "pesto",
    "acucar",
    "mel",
    "bacon",
    "chouric",
    "linguic",
    "alheira",
    "farinheira",
    "leite",
    "molho",
)
_SECONDARY_PROTEIN_MODIFIER_ROOTS = (
    "queijo",
    "bacon",
    "chouric",
    "linguic",
    "alheira",
    "farinheira",
)
_ACCESSORY_PHRASES = (
    "sal",
    "sal grosso",
    "pimenta",
    "pimenta preta",
    "pimenta branca",
    "alho",
    "alho em po",
    "louro",
    "salsa",
    "coentros",
    "colorau",
    "paprica",
    "noz moscada",
    "vinagre",
    "limao",
    "caldo",
    "vinho branco",
    "vinho tinto",
)


@dataclass(frozen=True)
class IngredientStructure:
    name: str
    quantity: str
    unit: str
    dimensions: tuple[str, ...]
    major_calorie_driver: bool


@dataclass(frozen=True)
class RecipeStructureProfile:
    recipe_name: str
    cooking_method: str
    primary_protein: str | None
    secondary_proteins: tuple[str, ...]
    primary_carbohydrate: str | None
    other_carbohydrates: tuple[str, ...]
    vegetables: tuple[str, ...]
    energy_modifiers: tuple[str, ...]
    accessories: tuple[str, ...]
    other_ingredients: tuple[str, ...]
    major_calorie_drivers: tuple[str, ...]
    ingredients: tuple[IngredientStructure, ...]


def _tokens(value: str) -> tuple[str, ...]:
    return tuple(normalize_food_text(value).split())


def _has_root(tokens: tuple[str, ...], roots: tuple[str, ...]) -> bool:
    return any(token.startswith(root) for token in tokens for root in roots)


def _has_phrase(value: str, phrases: tuple[str, ...]) -> bool:
    normalized = f" {normalize_food_text(value)} "
    return any(f" {normalize_food_text(phrase)} " in normalized for phrase in phrases)


def classify_ingredient_dimensions(name: str) -> tuple[str, ...]:
    tokens = _tokens(name)
    dimensions: list[str] = []

    if _has_root(tokens, _PROTEIN_ROOTS) or _has_root(
        tokens, _SECONDARY_PROTEIN_MODIFIER_ROOTS
    ):
        dimensions.append(DIM_PROTEIN)

    if _has_root(tokens, _CARB_ROOTS) or _has_root(tokens, _LEGUME_ROOTS):
        dimensions.append(DIM_CARBOHYDRATE)

    if _has_root(tokens, _LEGUME_ROOTS) and DIM_PROTEIN not in dimensions:
        dimensions.append(DIM_PROTEIN)

    if _has_root(tokens, _VEGETABLE_ROOTS):
        dimensions.append(DIM_VEGETABLE)

    if _has_root(tokens, _ENERGY_MODIFIER_ROOTS):
        dimensions.append(DIM_ENERGY_MODIFIER)

    if not dimensions and _has_phrase(name, _ACCESSORY_PHRASES):
        dimensions.append(DIM_ACCESSORY)

    if not dimensions:
        dimensions.append(DIM_OTHER)

    return tuple(dimensions)


def _infer_cooking_method(recipe: Recipe) -> str:
    texts = [recipe.name]
    texts.extend(
        value
        for ingredient in recipe.ingredients
        for value in (ingredient.preparation, ingredient.notes)
        if value
    )
    normalized = " ".join(normalize_food_text(value) for value in texts)

    if "actifry" in normalized or "air fryer" in normalized:
        return COOKING_AIR_FRIED
    if "frit" in normalized:
        return COOKING_FRIED
    if "grelh" in normalized:
        return COOKING_GRILLED
    if "forno" in normalized or "assad" in normalized:
        return COOKING_BAKED
    if "guisad" in normalized or "estufad" in normalized or "strogonoff" in normalized:
        return COOKING_STEWED
    if "cozid" in normalized:
        return COOKING_BOILED
    if "saltead" in normalized:
        return COOKING_SAUTEED
    return COOKING_UNKNOWN


def _name_overlap_score(recipe_name: str, ingredient_name: str) -> int:
    recipe_tokens = set(_tokens(recipe_name))
    ingredient_tokens = set(_tokens(ingredient_name))
    return len(recipe_tokens & ingredient_tokens)


def _select_primary(
    recipe_name: str,
    candidates: list[IngredientStructure],
    *,
    dimension: str,
) -> IngredientStructure | None:
    if not candidates:
        return None

    def rank(item: IngredientStructure) -> tuple[int, int, int]:
        mixed_penalty = int(len(item.dimensions) > 1)
        overlap = _name_overlap_score(recipe_name, item.name)
        modifier_penalty = int(DIM_ENERGY_MODIFIER in item.dimensions)
        if dimension == DIM_CARBOHYDRATE:
            modifier_penalty = 0
        return (-modifier_penalty, -mixed_penalty, overlap)

    return max(candidates, key=rank)


def build_recipe_structure_profile(recipe: Recipe) -> RecipeStructureProfile:
    ingredients = tuple(
        IngredientStructure(
            name=ingredient.food_item.name,
            quantity=str(ingredient.quantity),
            unit=ingredient.unit,
            dimensions=classify_ingredient_dimensions(ingredient.food_item.name),
            major_calorie_driver=bool(
                {
                    DIM_PROTEIN,
                    DIM_CARBOHYDRATE,
                    DIM_ENERGY_MODIFIER,
                }
                & set(classify_ingredient_dimensions(ingredient.food_item.name))
            ),
        )
        for ingredient in recipe.ingredients
    )

    proteins = [item for item in ingredients if DIM_PROTEIN in item.dimensions]
    carbs = [item for item in ingredients if DIM_CARBOHYDRATE in item.dimensions]
    vegetables = tuple(
        item.name for item in ingredients if DIM_VEGETABLE in item.dimensions
    )
    modifiers = tuple(
        item.name for item in ingredients if DIM_ENERGY_MODIFIER in item.dimensions
    )
    accessories = tuple(
        item.name for item in ingredients if DIM_ACCESSORY in item.dimensions
    )
    others = tuple(item.name for item in ingredients if DIM_OTHER in item.dimensions)

    primary_protein = _select_primary(
        recipe.name,
        proteins,
        dimension=DIM_PROTEIN,
    )
    primary_carb = _select_primary(
        recipe.name,
        carbs,
        dimension=DIM_CARBOHYDRATE,
    )

    return RecipeStructureProfile(
        recipe_name=recipe.name,
        cooking_method=_infer_cooking_method(recipe),
        primary_protein=primary_protein.name if primary_protein else None,
        secondary_proteins=tuple(
            item.name for item in proteins if item is not primary_protein
        ),
        primary_carbohydrate=primary_carb.name if primary_carb else None,
        other_carbohydrates=tuple(item.name for item in carbs if item is not primary_carb),
        vegetables=vegetables,
        energy_modifiers=modifiers,
        accessories=accessories,
        other_ingredients=others,
        major_calorie_drivers=tuple(
            item.name for item in ingredients if item.major_calorie_driver
        ),
        ingredients=ingredients,
    )


def load_legacy_recipes_for_structure(
    db: Session,
    *,
    recipe_key_prefix: str = "legacy-v1:",
) -> list[Recipe]:
    statement = (
        select(Recipe)
        .options(
            selectinload(Recipe.ingredients).selectinload(RecipeIngredient.food_item)
        )
        .where(
            Recipe.is_active.is_(True),
            Recipe.recipe_key.like(f"{recipe_key_prefix}%"),
        )
        .order_by(Recipe.name)
    )
    return list(db.scalars(statement))


def build_legacy_recipe_structure_profiles(
    db: Session,
    *,
    recipe_key_prefix: str = "legacy-v1:",
) -> tuple[RecipeStructureProfile, ...]:
    return tuple(
        build_recipe_structure_profile(recipe)
        for recipe in load_legacy_recipes_for_structure(
            db,
            recipe_key_prefix=recipe_key_prefix,
        )
    )
