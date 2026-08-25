from decimal import Decimal

from app.models.food_catalog import FoodItem, Recipe, RecipeIngredient
from app.services.recipe_structure_profile import (
    COOKING_AIR_FRIED,
    COOKING_STEWED,
    COOKING_UNKNOWN,
    DIM_ACCESSORY,
    DIM_CARBOHYDRATE,
    DIM_ENERGY_MODIFIER,
    DIM_PROTEIN,
    DIM_VEGETABLE,
    build_recipe_structure_profile,
    classify_ingredient_dimensions,
)


def _recipe(name: str, ingredients: list[str]) -> Recipe:
    recipe = Recipe(recipe_key=f"test:{name}", name=name, source="test")
    for index, ingredient_name in enumerate(ingredients):
        food = FoodItem(
            catalog_key=f"test:{index}:{ingredient_name}",
            name=ingredient_name,
            food_kind="ingredient",
            source="test",
        )
        recipe.ingredients.append(
            RecipeIngredient(
                food_item=food,
                quantity=Decimal(1),
                unit="un",
                sort_order=index,
            )
        )
    return recipe


def test_classification_focuses_on_nutritionally_relevant_dimensions() -> None:
    assert classify_ingredient_dimensions("Bacalhau desfiado") == (DIM_PROTEIN,)
    assert set(classify_ingredient_dimensions("Grão de bico")) == {
        DIM_PROTEIN,
        DIM_CARBOHYDRATE,
    }
    assert classify_ingredient_dimensions("Massa") == (DIM_CARBOHYDRATE,)
    assert classify_ingredient_dimensions("Cogumelos congelados") == (DIM_VEGETABLE,)
    assert classify_ingredient_dimensions("Natas") == (DIM_ENERGY_MODIFIER,)
    assert classify_ingredient_dimensions("Azeite") == (DIM_ENERGY_MODIFIER,)
    assert classify_ingredient_dimensions("Pimenta preta em pó") == (DIM_ACCESSORY,)
    assert classify_ingredient_dimensions("Sal grosso") == (DIM_ACCESSORY,)


def test_profile_identifies_primary_structure_and_ignores_accessories_as_drivers() -> None:
    recipe = _recipe(
        "Bacalhau com grão",
        [
            "Alho",
            "Azeite",
            "Bacalhau desfiado",
            "Cebola",
            "Grão de bico",
            "Ovos",
            "Pimenta branca",
            "Salsa",
            "Vinagre",
        ],
    )

    profile = build_recipe_structure_profile(recipe)

    assert profile.primary_protein == "Bacalhau desfiado"
    assert "Ovos" in profile.secondary_proteins
    assert "Grão de bico" in profile.secondary_proteins
    assert profile.primary_carbohydrate == "Grão de bico"
    assert "Cebola" in profile.vegetables
    assert profile.energy_modifiers == ("Azeite",)
    assert "Alho" in profile.accessories
    assert "Pimenta branca" in profile.accessories
    assert "Azeite" in profile.major_calorie_drivers
    assert "Pimenta branca" not in profile.major_calorie_drivers
    assert profile.cooking_method == COOKING_UNKNOWN


def test_profile_infers_common_cooking_method_from_recipe_name() -> None:
    stewed = _recipe(
        "Carne guisada com massa",
        ["Carne de vaca", "Massa", "Cenoura", "Azeite"],
    )
    air_fried = _recipe(
        "Carne de porco com cogumelos na actifry",
        ["Carne de porco", "Cogumelos", "Azeite"],
    )

    assert build_recipe_structure_profile(stewed).cooking_method == COOKING_STEWED
    assert build_recipe_structure_profile(air_fried).cooking_method == COOKING_AIR_FRIED


def test_cheese_and_processed_meat_can_be_protein_and_energy_modifier() -> None:
    cheese = classify_ingredient_dimensions("Queijo cheddar")
    bacon = classify_ingredient_dimensions("Bacon")

    assert DIM_PROTEIN in cheese
    assert DIM_ENERGY_MODIFIER in cheese
    assert DIM_PROTEIN in bacon
    assert DIM_ENERGY_MODIFIER in bacon
