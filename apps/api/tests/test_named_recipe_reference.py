from decimal import Decimal

from app.models.food_catalog import Recipe
from app.services.named_recipe_reference import known_named_recipe_reference
from app.services.recipe_nutrition import build_recipe_composition


def test_douradinhos_use_verified_iglo_portion_reference() -> None:
    recipe = Recipe(
        recipe_key="legacy-v1:recipe:douradinhos",
        name="Douradinhos",
        source="legacy-v1",
    )

    result = build_recipe_composition(recipe)
    composition = result.composition
    inputs = composition.calculation_inputs

    assert composition.energy_kcal == Decimal(184)
    assert composition.reference_quantity == Decimal(1)
    assert composition.reference_unit == "serving"
    assert isinstance(inputs, dict)
    assert inputs["nutrition_source"] == "external-product-reference"
    assert inputs["energy_estimated"] is False
    profile = inputs["practical_profile"]
    assert isinstance(profile, dict)
    assert profile["primary_protein"] == "Peixe branco panado (Douradinhos Iglo)"
    assert profile["primary_carbohydrate"] == "Panado"
    assert profile["suggested_accompaniments"] == ["arroz", "legumes", "salada"]


def test_lidl_meatloaf_stays_explicitly_low_confidence_when_variant_is_ambiguous() -> None:
    recipe = Recipe(
        recipe_key="legacy-v1:recipe:meatloaf",
        name="Rolo de carne do Lidl",
        source="legacy-v1",
    )

    result = build_recipe_composition(recipe)
    composition = result.composition
    inputs = composition.calculation_inputs

    assert composition.energy_kcal == Decimal(260)
    assert isinstance(inputs, dict)
    assert inputs["energy_estimated"] is True
    external = inputs["external_named_reference"]
    assert isinstance(external, dict)
    assert external["confidence"] == "low"
    assert external["suggested_accompaniments"] == ["salada", "puré", "massa", "arroz"]


def test_unknown_ingredientless_name_is_not_given_a_fake_reference() -> None:
    assert known_named_recipe_reference("Produto misterioso") is None
