from decimal import Decimal

from app.models.food_catalog import FoodItem, Recipe, RecipeIngredient
from app.services.recipe_structure_profile import (
    COOKING_AIR_FRIED,
    COOKING_BOILED,
    COOKING_FRIED,
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


def _recipe_rows(name: str, rows: list[tuple[str, Decimal, str]]) -> Recipe:
    recipe = Recipe(recipe_key=f"test:{name}", name=name, source="test")
    for index, (ingredient_name, quantity, unit) in enumerate(rows):
        food = FoodItem(
            catalog_key=f"test:{index}:{ingredient_name}",
            name=ingredient_name,
            food_kind="ingredient",
            source="test",
        )
        recipe.ingredients.append(
            RecipeIngredient(
                food_item=food,
                quantity=quantity,
                unit=unit,
                sort_order=index,
            )
        )
    return recipe


def test_classification_focuses_on_nutritionally_relevant_dimensions() -> None:
    assert classify_ingredient_dimensions("Bacalhau desfiado") == (DIM_PROTEIN,)
    assert classify_ingredient_dimensions("Rojões") == (DIM_PROTEIN,)
    assert classify_ingredient_dimensions("Entrecosto pedaços") == (DIM_PROTEIN,)
    assert classify_ingredient_dimensions("Escalopes de vitela") == (DIM_PROTEIN,)
    assert classify_ingredient_dimensions("Perca do nilo") == (DIM_PROTEIN,)
    assert set(classify_ingredient_dimensions("Salsichas frescas")) == {
        DIM_PROTEIN,
        DIM_ENERGY_MODIFIER,
    }
    assert set(classify_ingredient_dimensions("Grão de bico")) == {
        DIM_PROTEIN,
        DIM_CARBOHYDRATE,
    }
    assert set(classify_ingredient_dimensions("Iogurte natural")) == {
        DIM_PROTEIN,
        DIM_ENERGY_MODIFIER,
    }
    assert set(classify_ingredient_dimensions("Leite meio-gordo")) == {
        DIM_PROTEIN,
        DIM_ENERGY_MODIFIER,
    }
    assert set(classify_ingredient_dimensions("Frutos secos")) == {
        DIM_PROTEIN,
        DIM_ENERGY_MODIFIER,
    }
    assert classify_ingredient_dimensions("Banana") == (DIM_CARBOHYDRATE,)
    assert classify_ingredient_dimensions("Muesli") == (DIM_CARBOHYDRATE,)
    assert classify_ingredient_dimensions("Cereais de pequeno-almoço") == (
        DIM_CARBOHYDRATE,
    )
    assert classify_ingredient_dimensions("Frutos vermelhos") == (DIM_CARBOHYDRATE,)
    assert classify_ingredient_dimensions("Massa") == (DIM_CARBOHYDRATE,)
    assert classify_ingredient_dimensions("Macarronete") == (DIM_CARBOHYDRATE,)
    assert classify_ingredient_dimensions("Fettuccine") == (DIM_CARBOHYDRATE,)
    assert classify_ingredient_dimensions("Massa de pimentão") == (DIM_ACCESSORY,)
    assert classify_ingredient_dimensions("Cogumelos congelados") == (DIM_VEGETABLE,)
    assert classify_ingredient_dimensions("Alho francês") == (DIM_VEGETABLE,)
    assert classify_ingredient_dimensions("Natas") == (DIM_ENERGY_MODIFIER,)
    assert classify_ingredient_dimensions("Azeite") == (DIM_ENERGY_MODIFIER,)
    assert classify_ingredient_dimensions("Pimenta preta em pó") == (DIM_ACCESSORY,)
    assert classify_ingredient_dimensions("Sal grosso") == (DIM_ACCESSORY,)
    assert classify_ingredient_dimensions("Caldo de carne") == (DIM_ACCESSORY,)
    assert classify_ingredient_dimensions("Noz moscada") == (DIM_ACCESSORY,)
    assert classify_ingredient_dimensions("Orégãos") == (DIM_ACCESSORY,)
    assert classify_ingredient_dimensions("Alecrim") == (DIM_ACCESSORY,)
    assert classify_ingredient_dimensions("Tabasco verde") == (DIM_ACCESSORY,)


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


def test_breakfast_and_snack_profiles_identify_main_components() -> None:
    breakfast = _recipe(
        "Cereais, leite e banana",
        ["Cereais de pequeno-almoço", "Leite meio-gordo", "Banana"],
    )
    snack = _recipe(
        "Banana e frutos secos",
        ["Banana", "Frutos secos"],
    )

    breakfast_profile = build_recipe_structure_profile(breakfast)
    snack_profile = build_recipe_structure_profile(snack)

    assert breakfast_profile.primary_protein == "Leite meio-gordo"
    assert breakfast_profile.primary_carbohydrate == "Cereais de pequeno-almoço"
    assert "Banana" in breakfast_profile.other_carbohydrates
    assert snack_profile.primary_protein == "Frutos secos"
    assert snack_profile.primary_carbohydrate == "Banana"
    assert "Frutos secos" in snack_profile.energy_modifiers


def test_small_flour_thickener_does_not_become_main_carbohydrate() -> None:
    escalopes = _recipe_rows(
        "Escalopes ao vinho Madeira",
        [
            ("Escalopes de vitela", Decimal(800), "g"),
            ("Farinha de trigo 55", Decimal(62), "g"),
            ("Margarina", Decimal(100), "g"),
        ],
    )
    mac = _recipe_rows(
        "Mac and Cheese",
        [
            ("Farinha de trigo 55", Decimal(60), "g"),
            ("Massa cotovelos", Decimal(450), "g"),
            ("Queijo cheddar", Decimal(350), "g"),
        ],
    )

    escalopes_profile = build_recipe_structure_profile(escalopes)
    mac_profile = build_recipe_structure_profile(mac)

    assert escalopes_profile.primary_protein == "Escalopes de vitela"
    assert escalopes_profile.primary_carbohydrate is None
    assert "Farinha de trigo 55" in escalopes_profile.other_carbohydrates
    assert mac_profile.primary_carbohydrate == "Massa cotovelos"


def test_generic_fish_recipe_prefers_actual_fish_over_eggs() -> None:
    recipe = _recipe(
        "Peixe cozido",
        ["Ovos", "Pescada fresca", "Batatas"],
    )

    profile = build_recipe_structure_profile(recipe)

    assert profile.primary_protein == "Pescada fresca"
    assert "Ovos" in profile.secondary_proteins


def test_qualitative_energy_modifier_is_not_a_major_calorie_driver() -> None:
    recipe = Recipe(recipe_key="test:milk", name="Bacalhau cremoso", source="test")
    milk = FoodItem(
        catalog_key="test:milk:item",
        name="Leite",
        food_kind="ingredient",
        source="test",
    )
    recipe.ingredients.append(
        RecipeIngredient(
            food_item=milk,
            quantity=Decimal(1),
            unit="qb",
            sort_order=0,
        )
    )

    profile = build_recipe_structure_profile(recipe)

    assert profile.energy_modifiers == ("Leite",)
    assert profile.major_calorie_drivers == ()


def test_profile_infers_common_cooking_method() -> None:
    stewed = _recipe(
        "Carne guisada com massa",
        ["Carne de vaca", "Massa", "Cenoura", "Azeite"],
    )
    air_fried = _recipe(
        "Carne de porco com cogumelos na actifry",
        ["Carne de porco", "Cogumelos", "Azeite"],
    )
    rice = _recipe(
        "Arroz de bacalhau",
        ["Arroz", "Bacalhau"],
    )
    chili = _recipe(
        "Chili",
        ["Carne picada", "Feijão vermelho"],
    )
    fried = _recipe(
        "Carne de porco à portuguesa",
        ["Rojões", "Batatas fritar", "Azeite"],
    )

    assert build_recipe_structure_profile(stewed).cooking_method == COOKING_STEWED
    assert build_recipe_structure_profile(air_fried).cooking_method == COOKING_AIR_FRIED
    assert build_recipe_structure_profile(rice).cooking_method == COOKING_BOILED
    assert build_recipe_structure_profile(chili).cooking_method == COOKING_STEWED
    assert build_recipe_structure_profile(fried).cooking_method == COOKING_FRIED


def test_cheese_and_processed_meat_can_be_protein_and_energy_modifier() -> None:
    cheese = classify_ingredient_dimensions("Queijo cheddar")
    bacon = classify_ingredient_dimensions("Bacon")
    sausage = classify_ingredient_dimensions("Salsichas frescas")
    ham = classify_ingredient_dimensions("Fiambre aos cubos")

    assert DIM_PROTEIN in cheese
    assert DIM_ENERGY_MODIFIER in cheese
    assert DIM_PROTEIN in bacon
    assert DIM_ENERGY_MODIFIER in bacon
    assert DIM_PROTEIN in sausage
    assert DIM_ENERGY_MODIFIER in sausage
    assert DIM_PROTEIN in ham
    assert DIM_ENERGY_MODIFIER in ham
