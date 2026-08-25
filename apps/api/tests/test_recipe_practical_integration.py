from datetime import UTC, datetime
from decimal import Decimal

from app.models.food_catalog import (
    FoodCompositionSnapshot,
    FoodItem,
    Recipe,
    RecipeIngredient,
)
from app.services.recipe_nutrition import CALCULATION_VERSION, build_recipe_composition


def _food(
    key: str,
    name: str,
    *,
    energy_per_100g: Decimal | None,
) -> FoodItem:
    item = FoodItem(
        catalog_key=key,
        name=name,
        food_kind="ingredient",
        source="test",
    )
    if energy_per_100g is not None:
        item.compositions.append(
            FoodCompositionSnapshot(
                reference_quantity=Decimal(100),
                reference_unit="g",
                energy_kcal=energy_per_100g,
                data_version=f"test-{key}",
                source="test",
                effective_at=datetime.now(UTC),
            )
        )
    return item


def _ingredient(food: FoodItem, quantity: Decimal, unit: str, order: int) -> RecipeIngredient:
    return RecipeIngredient(
        food_item=food,
        quantity=quantity,
        unit=unit,
        sort_order=order,
    )


def test_incomplete_exact_composition_falls_back_to_practical_energy_for_planning() -> None:
    turkey = _food("turkey", "Bifes de peru", energy_per_100g=Decimal(140))
    margarine = _food("margarine", "Margarina", energy_per_100g=None)
    recipe = Recipe(
        recipe_key="test:turkey",
        name="Bifes de peru com limão",
        source="test",
    )
    recipe.ingredients.extend(
        [
            _ingredient(turkey, Decimal(800), "g", 0),
            _ingredient(margarine, Decimal(100), "g", 1),
        ]
    )

    result = build_recipe_composition(recipe)
    composition = result.composition
    inputs = composition.calculation_inputs

    assert composition.calculation_version == CALCULATION_VERSION
    assert composition.energy_kcal is not None
    assert composition.reference_quantity == Decimal(5)
    assert composition.reference_unit == "serving"
    assert isinstance(inputs, dict)
    assert inputs["practical_energy_used"] is True
    assert inputs["energy_estimated"] is True
    assert inputs["serving_count_estimated"] is True
    practical_energy = inputs["practical_energy"]
    assert isinstance(practical_energy, dict)
    assert practical_energy["serving_count_source"] == "practical-portion-inference"
    profile = inputs["practical_profile"]
    assert isinstance(profile, dict)
    assert profile["primary_protein"] == "Bifes de peru"
    assert profile["energy_load_signal"] in {"moderate", "high"}


def test_exact_total_energy_is_kept_but_missing_servings_get_practical_serving_reference() -> None:
    cod = _food("cod", "Bacalhau desfiado", energy_per_100g=Decimal(100))
    rice = _food("rice", "Arroz agulha", energy_per_100g=Decimal(350))
    recipe = Recipe(
        recipe_key="test:cod-rice",
        name="Arroz de bacalhau",
        source="test",
    )
    recipe.ingredients.extend(
        [
            _ingredient(cod, Decimal(400), "g", 0),
            _ingredient(rice, Decimal(280), "g", 1),
        ]
    )

    composition = build_recipe_composition(recipe).composition
    inputs = composition.calculation_inputs

    assert composition.energy_kcal == Decimal(1380)
    assert composition.reference_quantity == Decimal(4)
    assert composition.reference_unit == "serving"
    assert isinstance(inputs, dict)
    assert inputs["practical_energy_used"] is False
    assert inputs["serving_count_estimated"] is True


def test_named_prepared_food_without_ingredients_uses_external_reference() -> None:
    recipe = Recipe(recipe_key="test:empty", name="Douradinhos", source="test")

    composition = build_recipe_composition(recipe).composition
    inputs = composition.calculation_inputs

    assert composition.energy_kcal == Decimal(184)
    assert composition.reference_quantity == Decimal(1)
    assert composition.reference_unit == "serving"
    assert isinstance(inputs, dict)
    assert inputs["nutrition_source"] == "external-product-reference"
    profile = inputs["practical_profile"]
    assert isinstance(profile, dict)
    assert profile["primary_protein"] == "Peixe branco panado (Douradinhos Iglo)"
    assert profile["suggested_accompaniments"] == ["arroz", "legumes", "salada"]


def test_unknown_empty_recipe_still_does_not_invent_energy() -> None:
    recipe = Recipe(recipe_key="test:unknown-empty", name="Produto sem dados", source="test")

    composition = build_recipe_composition(recipe).composition
    inputs = composition.calculation_inputs

    assert composition.energy_kcal is None
    assert isinstance(inputs, dict)
    profile = inputs["practical_profile"]
    assert isinstance(profile, dict)
    assert profile["balance_signals"] == ["insufficient_data"]
