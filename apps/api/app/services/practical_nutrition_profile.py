from dataclasses import dataclass
from decimal import Decimal

from app.models.food_catalog import Recipe
from app.services.nutrition_learning import normalize_food_text
from app.services.recipe_nutrition import QUALITATIVE_UNITS
from app.services.recipe_structure_profile import (
    COOKING_AIR_FRIED,
    COOKING_FRIED,
    DIM_CARBOHYDRATE,
    IngredientStructure,
    RecipeStructureProfile,
    build_recipe_structure_profile,
)
from app.services.retail_quantity_estimates import PACKAGE_UNITS

LOAD_NONE = "none"
LOAD_LOW = "low"
LOAD_MODERATE = "moderate"
LOAD_HIGH = "high"
LOAD_UNKNOWN = "unknown"

MODIFIER_ADDED_FAT = "added_fat"
MODIFIER_RICH_SAUCE = "rich_sauce"
MODIFIER_CHEESE = "cheese"
MODIFIER_PROCESSED_MEAT = "processed_meat"
MODIFIER_SWEETENER = "sweetener"
MODIFIER_OTHER = "other"

PATTERN_NONE = "none"
PATTERN_SINGLE = "single"
PATTERN_MIXED = "mixed"

VEGETABLE_NONE = "none"
VEGETABLE_LOW = "low"
VEGETABLE_MODERATE = "moderate"
VEGETABLE_HIGH = "high"

ENERGY_SIGNAL_LOW = "low"
ENERGY_SIGNAL_MODERATE = "moderate"
ENERGY_SIGNAL_HIGH = "high"

_ADDED_FAT_ROOTS = ("azeite", "oleo", "manteig", "margarin")
_RICH_SAUCE_ROOTS = ("natas", "maiones", "pesto", "molho", "bechamel")
_CHEESE_ROOTS = ("queijo",)
_PROCESSED_MEAT_ROOTS = (
    "bacon",
    "chouric",
    "linguic",
    "alheira",
    "farinheira",
)
_SWEETENER_ROOTS = ("acucar", "mel")


@dataclass(frozen=True)
class PracticalModifier:
    name: str
    kind: str
    quantity: str
    unit: str
    load: str


@dataclass(frozen=True)
class PracticalNutritionProfile:
    recipe_name: str
    cooking_method: str
    primary_protein: str | None
    secondary_proteins: tuple[str, ...]
    protein_pattern: str
    primary_carbohydrate: str | None
    other_carbohydrates: tuple[str, ...]
    carbohydrate_pattern: str
    vegetables: tuple[str, ...]
    vegetable_level: str
    modifiers: tuple[PracticalModifier, ...]
    energy_load_signal: str
    balance_signals: tuple[str, ...]
    calorie_drivers: tuple[str, ...]


def _starts_with_any(value: str, roots: tuple[str, ...]) -> bool:
    tokens = normalize_food_text(value).split()
    return any(token.startswith(root) for token in tokens for root in roots)


def _modifier_kind(name: str) -> str:
    if _starts_with_any(name, _ADDED_FAT_ROOTS):
        return MODIFIER_ADDED_FAT
    if _starts_with_any(name, _RICH_SAUCE_ROOTS):
        return MODIFIER_RICH_SAUCE
    if _starts_with_any(name, _CHEESE_ROOTS):
        return MODIFIER_CHEESE
    if _starts_with_any(name, _PROCESSED_MEAT_ROOTS):
        return MODIFIER_PROCESSED_MEAT
    if _starts_with_any(name, _SWEETENER_ROOTS):
        return MODIFIER_SWEETENER
    return MODIFIER_OTHER


def _numeric_load(
    *,
    kind: str,
    quantity: Decimal,
    unit: str,
) -> str:
    normalized_unit = unit.strip().casefold()
    if normalized_unit in QUALITATIVE_UNITS:
        return LOAD_NONE
    if normalized_unit in PACKAGE_UNITS:
        return LOAD_HIGH if quantity >= 2 else LOAD_MODERATE
    if normalized_unit not in {"g", "ml"}:
        return LOAD_UNKNOWN

    thresholds = {
        MODIFIER_ADDED_FAT: (Decimal(30), Decimal(75)),
        MODIFIER_RICH_SAUCE: (Decimal(100), Decimal(250)),
        MODIFIER_CHEESE: (Decimal(30), Decimal(75)),
        MODIFIER_PROCESSED_MEAT: (Decimal(50), Decimal(120)),
        MODIFIER_SWEETENER: (Decimal(20), Decimal(60)),
        MODIFIER_OTHER: (Decimal(50), Decimal(150)),
    }
    low_max, moderate_max = thresholds[kind]
    if quantity <= low_max:
        return LOAD_LOW
    if quantity <= moderate_max:
        return LOAD_MODERATE
    return LOAD_HIGH


def _pattern(primary: str | None, secondary: tuple[str, ...]) -> str:
    if primary is None:
        return PATTERN_NONE
    return PATTERN_MIXED if secondary else PATTERN_SINGLE


def _vegetable_level(vegetables: tuple[str, ...]) -> str:
    count = len(set(vegetables))
    if count == 0:
        return VEGETABLE_NONE
    if count == 1:
        return VEGETABLE_LOW
    if count <= 3:
        return VEGETABLE_MODERATE
    return VEGETABLE_HIGH


def _carbohydrate_load(item: IngredientStructure) -> int:
    if DIM_CARBOHYDRATE not in item.dimensions:
        return 0
    unit = item.unit.strip().casefold()
    if unit in QUALITATIVE_UNITS:
        return 0
    try:
        quantity = Decimal(item.quantity)
    except ArithmeticError:
        return 0
    if unit in PACKAGE_UNITS:
        return 2 if quantity >= 2 else 1
    if unit != "g":
        return 1
    if quantity > 350:
        return 2
    if quantity >= 150:
        return 1
    return 0


def _energy_load_signal(
    structure: RecipeStructureProfile,
    modifiers: tuple[PracticalModifier, ...],
) -> str:
    score = 0
    if structure.cooking_method == COOKING_FRIED:
        score += 3
    elif structure.cooking_method == COOKING_AIR_FRIED:
        score += 1

    for modifier in modifiers:
        if modifier.load == LOAD_HIGH:
            score += 2
        elif modifier.load == LOAD_MODERATE:
            score += 1
        if modifier.kind == MODIFIER_RICH_SAUCE and modifier.load in {
            LOAD_MODERATE,
            LOAD_HIGH,
        }:
            score += 1

    score += sum(
        _carbohydrate_load(item)
        for item in structure.ingredients
        if DIM_CARBOHYDRATE in item.dimensions
    )

    if score >= 4:
        return ENERGY_SIGNAL_HIGH
    if score >= 2:
        return ENERGY_SIGNAL_MODERATE
    return ENERGY_SIGNAL_LOW


def _balance_signals(
    *,
    structure: RecipeStructureProfile,
    protein_pattern: str,
    carbohydrate_pattern: str,
    vegetable_level: str,
    modifiers: tuple[PracticalModifier, ...],
    energy_load_signal: str,
) -> tuple[str, ...]:
    signals: list[str] = []
    if protein_pattern == PATTERN_NONE:
        signals.append("protein_missing")
    elif protein_pattern == PATTERN_MIXED:
        signals.append("mixed_protein")

    if carbohydrate_pattern == PATTERN_NONE:
        signals.append("carb_light")
    elif carbohydrate_pattern == PATTERN_MIXED:
        signals.append("mixed_carbohydrate")

    if vegetable_level == VEGETABLE_NONE:
        signals.append("vegetables_missing")
    elif vegetable_level == VEGETABLE_LOW:
        signals.append("vegetables_light")

    if any(item.kind == MODIFIER_RICH_SAUCE for item in modifiers):
        signals.append("rich_sauce")
    if any(item.load == LOAD_HIGH for item in modifiers):
        signals.append("high_energy_modifier")
    if structure.cooking_method == COOKING_FRIED:
        signals.append("fried")

    if (
        protein_pattern != PATTERN_NONE
        and carbohydrate_pattern != PATTERN_NONE
        and vegetable_level in {VEGETABLE_MODERATE, VEGETABLE_HIGH}
        and energy_load_signal != ENERGY_SIGNAL_HIGH
    ):
        signals.append("structurally_balanced")

    return tuple(signals)


def build_practical_nutrition_profile(recipe: Recipe) -> PracticalNutritionProfile:
    structure = build_recipe_structure_profile(recipe)
    by_name = {item.name: item for item in structure.ingredients}
    modifiers = tuple(
        PracticalModifier(
            name=name,
            kind=_modifier_kind(name),
            quantity=by_name[name].quantity,
            unit=by_name[name].unit,
            load=_numeric_load(
                kind=_modifier_kind(name),
                quantity=Decimal(by_name[name].quantity),
                unit=by_name[name].unit,
            ),
        )
        for name in structure.energy_modifiers
    )
    protein_pattern = _pattern(
        structure.primary_protein,
        structure.secondary_proteins,
    )
    carbohydrate_pattern = _pattern(
        structure.primary_carbohydrate,
        structure.other_carbohydrates,
    )
    vegetable_level = _vegetable_level(structure.vegetables)
    energy_load_signal = _energy_load_signal(structure, modifiers)

    return PracticalNutritionProfile(
        recipe_name=recipe.name,
        cooking_method=structure.cooking_method,
        primary_protein=structure.primary_protein,
        secondary_proteins=structure.secondary_proteins,
        protein_pattern=protein_pattern,
        primary_carbohydrate=structure.primary_carbohydrate,
        other_carbohydrates=structure.other_carbohydrates,
        carbohydrate_pattern=carbohydrate_pattern,
        vegetables=structure.vegetables,
        vegetable_level=vegetable_level,
        modifiers=modifiers,
        energy_load_signal=energy_load_signal,
        balance_signals=_balance_signals(
            structure=structure,
            protein_pattern=protein_pattern,
            carbohydrate_pattern=carbohydrate_pattern,
            vegetable_level=vegetable_level,
            modifiers=modifiers,
            energy_load_signal=energy_load_signal,
        ),
        calorie_drivers=structure.major_calorie_drivers,
    )
