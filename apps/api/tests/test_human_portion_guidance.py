from datetime import UTC, datetime
from decimal import Decimal

from app.models.food_catalog import (
    FoodItem,
    Recipe,
    RecipeCompositionSnapshot,
    RecipeIngredient,
)
from app.services.human_portion_guidance import build_human_portion_guidance
from app.services.meal_recommendation import build_recipe_candidate

NOW = datetime(2026, 8, 25, 10, 0, tzinfo=UTC)


def _ingredient(key: str, name: str) -> FoodItem:
    return FoodItem(
        catalog_key=key,
        name=name,
        food_kind="ingredient",
        source="test",
    )


def test_recipe_guidance_exposes_scaled_components_instead_of_decimal_servings() -> None:
    coffee = _ingredient("test:coffee", "Café")
    milk = _ingredient("test:milk", "Leite meio-gordo")
    bread = _ingredient("test:bread", "Pão para torrada")
    butter = _ingredient("test:butter", "Manteiga")
    recipe = Recipe(
        recipe_key="test:breakfast",
        name="Café com leite e torrada com manteiga",
        serving_count=Decimal(1),
        source="test",
    )
    recipe.ingredients.extend(
        [
            RecipeIngredient(food_item=coffee, quantity=Decimal(60), unit="ml", sort_order=0),
            RecipeIngredient(food_item=milk, quantity=Decimal(180), unit="ml", sort_order=1),
            RecipeIngredient(food_item=bread, quantity=Decimal(60), unit="g", sort_order=2),
            RecipeIngredient(food_item=butter, quantity=Decimal(10), unit="g", sort_order=3),
        ]
    )
    composition = RecipeCompositionSnapshot(
        recipe=recipe,
        reference_quantity=Decimal(1),
        reference_unit="serving",
        energy_kcal=Decimal(285),
        composition_version="test-v1",
        calculation_version="test",
        computed_at=NOW,
    )
    candidate = build_recipe_candidate(
        composition,
        quantity=Decimal("1.25"),
        quantity_unit="serving",
    )

    guidance = build_human_portion_guidance(candidate)

    assert guidance is not None
    assert guidance.kind == "recipe_components"
    assert [(item.name, item.quantity, item.unit) for item in guidance.components] == [
        ("Café", Decimal("75.00"), "ml"),
        ("Leite meio-gordo", Decimal("225.00"), "ml"),
        ("Pão para torrada", Decimal("75.00"), "g"),
        ("Manteiga", Decimal("12.50"), "g"),
    ]


def test_recipe_guidance_keeps_quanto_baste_qualitative() -> None:
    salt = _ingredient("test:salt", "Sal")
    recipe = Recipe(
        recipe_key="test:soup",
        name="Sopa",
        serving_count=Decimal(4),
        source="test",
    )
    recipe.ingredients.append(
        RecipeIngredient(food_item=salt, quantity=Decimal(1), unit="qb", sort_order=0)
    )
    composition = RecipeCompositionSnapshot(
        recipe=recipe,
        reference_quantity=Decimal(4),
        reference_unit="serving",
        energy_kcal=Decimal(400),
        composition_version="test-v1",
        calculation_version="test",
        computed_at=NOW,
    )
    candidate = build_recipe_candidate(
        composition,
        quantity=Decimal(1),
        quantity_unit="serving",
    )

    guidance = build_human_portion_guidance(candidate)

    assert guidance is not None
    component = guidance.components[0]
    assert component.name == "Sal"
    assert component.quantity is None
    assert component.unit == "qb"
    assert component.qualitative is True
