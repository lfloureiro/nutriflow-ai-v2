import json
from datetime import UTC, datetime
from decimal import Decimal

from app.models.food_catalog import (
    FoodCompositionSnapshot,
    FoodItem,
    Recipe,
    RecipeIngredient,
)
from app.services.recipe_nutrition import build_recipe_composition

NOW = datetime(2026, 8, 24, 12, 0, tzinfo=UTC)


def _ingredient(*, with_portion_conversion: bool) -> FoodItem:
    notes = None
    if with_portion_conversion:
        notes = json.dumps(
            {
                "portion_conversions": {
                    "un": {
                        "reference_unit": "g",
                        "quantity_in_reference_unit": "25",
                        "source": "usda-fdc",
                        "source_reference": "https://fdc.example/123",
                        "fdc_portion_description": "1 meatball",
                    }
                }
            }
        )
    item = FoodItem(
        catalog_key="shared:ingredient:meatball",
        name="Almôndega",
        food_kind="ingredient",
        source="legacy-v1",
    )
    item.compositions.append(
        FoodCompositionSnapshot(
            reference_quantity=Decimal(100),
            reference_unit="g",
            energy_kcal=Decimal(200),
            data_version="usda-test",
            source="usda-fdc",
            source_reference="https://fdc.example/123",
            effective_at=NOW,
            notes=notes,
        )
    )
    return item


def _recipe(item: FoodItem) -> Recipe:
    recipe = Recipe(
        recipe_key="recipe:test:meatballs",
        name="Almôndegas teste",
        serving_count=Decimal(1),
        source="test",
    )
    recipe.ingredients.append(
        RecipeIngredient(
            food_item=item,
            quantity=Decimal(4),
            unit="un",
            sort_order=0,
        )
    )
    return recipe


def test_recipe_uses_explicit_portion_conversion_for_unit_counts() -> None:
    result = build_recipe_composition(
        _recipe(_ingredient(with_portion_conversion=True))
    )

    assert result.issues == ()
    assert result.composition.energy_kcal == Decimal(200)
    assert result.composition.calculation_inputs is not None
    ingredient_input = result.composition.calculation_inputs["ingredients"][0]
    conversion = ingredient_input["portion_conversion"]
    assert conversion["recipe_unit"] == "un"
    assert conversion["reference_unit"] == "g"
    assert conversion["quantity_in_reference_unit"] == "25"
    assert conversion["source"] == "usda-fdc"
    assert conversion["description"] == "1 meatball"


def test_recipe_uses_explicitly_estimated_energy_when_safe_unit_conversion_is_missing() -> None:
    result = build_recipe_composition(
        _recipe(_ingredient(with_portion_conversion=False))
    )

    assert result.composition.energy_kcal == Decimal(280)
    assert result.composition.calculation_inputs is not None
    inputs = result.composition.calculation_inputs
    assert inputs["practical_energy_used"] is True
    assert inputs["energy_estimated"] is True
    assert any("cannot be safely converted" in issue for issue in result.issues)
    assert any("practical estimate" in issue for issue in result.issues)


def test_recipe_estimates_unknown_package_for_four_servings() -> None:
    item = FoodItem(
        catalog_key="shared:ingredient:package-test",
        name="Ingrediente embalado desconhecido",
        food_kind="ingredient",
        source="test",
    )
    item.compositions.append(
        FoodCompositionSnapshot(
            reference_quantity=Decimal(100),
            reference_unit="g",
            energy_kcal=Decimal(50),
            data_version="package-test",
            source="portfir",
            source_reference="https://portfir.example/item",
            effective_at=NOW,
        )
    )
    recipe = Recipe(
        recipe_key="recipe:test:package",
        name="Receita embalagem",
        serving_count=Decimal(4),
        source="test",
    )
    recipe.ingredients.append(
        RecipeIngredient(
            food_item=item,
            quantity=Decimal(1),
            unit="emb",
            sort_order=0,
        )
    )

    result = build_recipe_composition(recipe)

    assert result.composition.energy_kcal == Decimal(200)
    assert result.composition.calculation_inputs is not None
    assert result.composition.calculation_inputs["energy_estimated"] is True
    ingredient_input = result.composition.calculation_inputs["ingredients"][0]
    conversion = ingredient_input["portion_conversion"]
    assert conversion["reference_unit"] == "g"
    assert conversion["quantity_in_reference_unit"] == "400"
    assert conversion["source"] == "retail-heuristic"
    assert conversion["confidence"] == "low"
    assert conversion["estimated"] is True
