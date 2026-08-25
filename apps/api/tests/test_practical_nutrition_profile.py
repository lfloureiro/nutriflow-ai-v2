from decimal import Decimal

from app.models.food_catalog import FoodItem, Recipe, RecipeIngredient
from app.services.practical_nutrition_profile import (
    ENERGY_SIGNAL_HIGH,
    ENERGY_SIGNAL_LOW,
    ENERGY_SIGNAL_MODERATE,
    ENERGY_SIGNAL_UNKNOWN,
    LOAD_HIGH,
    LOAD_LOW,
    LOAD_MODERATE,
    MODIFIER_ADDED_FAT,
    MODIFIER_RICH_SAUCE,
    PATTERN_MIXED,
    VEGETABLE_LOW,
    VEGETABLE_MODERATE,
    build_practical_nutrition_profile,
    score_practical_nutrition_profile,
)


def _recipe(name: str, rows: list[tuple[str, Decimal, str]]) -> Recipe:
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


def test_profile_highlights_large_added_fat_without_caring_about_accessories() -> None:
    recipe = _recipe(
        "Bacalhau com grão",
        [
            ("Bacalhau desfiado", Decimal(400), "g"),
            ("Lata de grão", Decimal(2), "emb"),
            ("Ovos", Decimal(4), "un"),
            ("Azeite", Decimal(300), "ml"),
            ("Alho", Decimal(4), "un"),
            ("Pimenta branca", Decimal(1), "qb"),
            ("Cebola", Decimal(1), "un"),
        ],
    )

    profile = build_practical_nutrition_profile(recipe)

    assert profile.protein_pattern == PATTERN_MIXED
    assert profile.vegetable_level == VEGETABLE_LOW
    assert profile.modifiers[0].kind == MODIFIER_ADDED_FAT
    assert profile.modifiers[0].load == LOAD_HIGH
    assert profile.energy_load_signal == ENERGY_SIGNAL_HIGH
    assert "high_energy_modifier" in profile.balance_signals


def test_profile_treats_typical_oil_amount_as_low_modifier_load() -> None:
    recipe = _recipe(
        "Arroz de bacalhau",
        [
            ("Bacalhau desfiado", Decimal(400), "g"),
            ("Arroz agulha", Decimal(280), "g"),
            ("Cebola", Decimal(1), "un"),
            ("Pimento verde", Decimal(1), "un"),
            ("Tomate pelado", Decimal(400), "g"),
            ("Azeite", Decimal(30), "ml"),
        ],
    )

    profile = build_practical_nutrition_profile(recipe)

    modifier = next(item for item in profile.modifiers if item.name == "Azeite")
    assert modifier.kind == MODIFIER_ADDED_FAT
    assert modifier.load == LOAD_LOW
    assert profile.energy_load_signal == ENERGY_SIGNAL_MODERATE
    assert profile.vegetable_level == VEGETABLE_MODERATE
    assert "structurally_balanced" in profile.balance_signals


def test_profile_marks_multiple_cream_packages_as_rich_sauce() -> None:
    recipe = _recipe(
        "Bifanas com natas",
        [
            ("Bifanas", Decimal(800), "g"),
            ("Margarina", Decimal(50), "g"),
            ("Natas", Decimal(3), "emb"),
        ],
    )

    profile = build_practical_nutrition_profile(recipe)

    margarine = next(item for item in profile.modifiers if item.name == "Margarina")
    cream = next(item for item in profile.modifiers if item.name == "Natas")
    assert margarine.load == LOAD_MODERATE
    assert cream.kind == MODIFIER_RICH_SAUCE
    assert cream.load == LOAD_HIGH
    assert profile.energy_load_signal == ENERGY_SIGNAL_HIGH
    assert "rich_sauce" in profile.balance_signals


def test_qualitative_modifier_does_not_raise_energy_load() -> None:
    recipe = _recipe(
        "Peixe com leite",
        [
            ("Pescada", Decimal(400), "g"),
            ("Leite", Decimal(1), "qb"),
        ],
    )

    profile = build_practical_nutrition_profile(recipe)

    milk = next(item for item in profile.modifiers if item.name == "Leite")
    assert milk.load == "none"
    assert profile.energy_load_signal == ENERGY_SIGNAL_LOW


def test_empty_recipe_is_marked_as_insufficient_data() -> None:
    recipe = Recipe(recipe_key="test:empty", name="Douradinhos", source="test")

    profile = build_practical_nutrition_profile(recipe)
    score, reasons = score_practical_nutrition_profile(profile)

    assert profile.energy_load_signal == ENERGY_SIGNAL_UNKNOWN
    assert profile.balance_signals == ("insufficient_data",)
    assert score == Decimal("0.0000")
    assert reasons == ("meal_structure:insufficient_data",)


def test_structure_score_prefers_balanced_recipe_over_rich_high_energy_recipe() -> None:
    balanced = build_practical_nutrition_profile(
        _recipe(
            "Arroz de bacalhau",
            [
                ("Bacalhau", Decimal(400), "g"),
                ("Arroz", Decimal(280), "g"),
                ("Cebola", Decimal(1), "un"),
                ("Tomate", Decimal(400), "g"),
                ("Azeite", Decimal(30), "ml"),
            ],
        )
    )
    rich = build_practical_nutrition_profile(
        _recipe(
            "Bifanas com natas",
            [
                ("Bifanas", Decimal(800), "g"),
                ("Margarina", Decimal(100), "g"),
                ("Natas", Decimal(3), "emb"),
            ],
        )
    )

    balanced_score, balanced_reasons = score_practical_nutrition_profile(balanced)
    rich_score, rich_reasons = score_practical_nutrition_profile(rich)

    assert balanced_score > rich_score
    assert "meal_structure:balanced" in balanced_reasons
    assert "meal_structure:high_energy_load" in rich_reasons
