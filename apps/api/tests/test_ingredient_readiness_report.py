from datetime import UTC, datetime
from decimal import Decimal

from app.models.food_catalog import FoodCompositionSnapshot, FoodItem, Recipe, RecipeIngredient
from app.services.ingredient_readiness_report import (
    BLOCKER_MISSING_COMPOSITION,
    BLOCKER_MISSING_CONVERSION,
    BLOCKER_MISSING_ENERGY,
    STATUS_BLOCKED,
    STATUS_READY,
    analyze_ingredient_readiness,
)


def _food(
    key: str,
    name: str,
    *,
    energy: Decimal | None = Decimal(100),
    reference_unit: str = "g",
) -> FoodItem:
    item = FoodItem(
        catalog_key=key,
        name=name,
        food_kind="ingredient",
        source="test",
    )
    if energy is not None or reference_unit:
        item.compositions.append(
            FoodCompositionSnapshot(
                reference_quantity=Decimal(100),
                reference_unit=reference_unit,
                energy_kcal=energy,
                data_version=f"test-{key}",
                source="test",
                effective_at=datetime.now(UTC),
            )
        )
    return item


def _missing_food(key: str, name: str) -> FoodItem:
    return FoodItem(
        catalog_key=key,
        name=name,
        food_kind="ingredient",
        source="test",
    )


def _recipe(key: str, name: str, rows: list[tuple[FoodItem, Decimal, str]]) -> Recipe:
    recipe = Recipe(recipe_key=key, name=name, source="test")
    for index, (food, quantity, unit) in enumerate(rows):
        recipe.ingredients.append(
            RecipeIngredient(
                food_item=food,
                quantity=quantity,
                unit=unit,
                sort_order=index,
            )
        )
    return recipe


def test_readiness_distinguishes_composition_energy_conversion_and_qualitative() -> None:
    ready = _food("ready", "Arroz")
    missing_composition = _missing_food("missing-composition", "Azeite")
    missing_energy = _food("missing-energy", "Natas", energy=None)
    needs_conversion = _food("needs-conversion", "Cebola")
    qualitative = _missing_food("qualitative", "Sal")

    recipe = _recipe(
        "legacy-v1:test",
        "Teste",
        [
            (ready, Decimal(100), "g"),
            (missing_composition, Decimal(30), "ml"),
            (missing_energy, Decimal(100), "g"),
            (needs_conversion, Decimal(1), "un"),
            (qualitative, Decimal(1), "qb"),
        ],
    )

    report = analyze_ingredient_readiness([recipe])
    item = report.recipes[0]

    assert item.status == STATUS_BLOCKED
    assert item.quantitative_count == 4
    assert item.qualitative_count == 1
    assert item.ready_quantitative_count == 1
    assert item.missing_composition_count == 1
    assert item.missing_energy_count == 1
    assert item.missing_conversion_count == 1
    assert item.blocker_count == 3

    blockers = {
        ingredient.ingredient_name: ingredient.blockers
        for ingredient in item.ingredients
    }
    assert blockers["Azeite"] == (BLOCKER_MISSING_COMPOSITION,)
    assert blockers["Natas"] == (BLOCKER_MISSING_ENERGY,)
    assert blockers["Cebola"] == (BLOCKER_MISSING_CONVERSION,)
    assert blockers["Sal"] == ()


def test_readiness_marks_recipe_ready_when_all_quantitative_ingredients_scale() -> None:
    rice = _food("rice", "Arroz")
    salt = _missing_food("salt", "Sal")
    recipe = _recipe(
        "legacy-v1:ready",
        "Arroz simples",
        [
            (rice, Decimal(200), "g"),
            (salt, Decimal(1), "qb"),
        ],
    )

    report = analyze_ingredient_readiness([recipe])

    assert report.recipes[0].status == STATUS_READY
    assert report.ready_recipe_count == 1
    assert report.blocked_recipe_count == 0


def test_priority_counts_affected_recipes_and_solo_unlocks() -> None:
    missing_a = _missing_food("a", "Azeite")
    missing_b = _missing_food("b", "Ovos")

    recipe_one = _recipe(
        "legacy-v1:one",
        "Receita um",
        [(missing_a, Decimal(30), "ml")],
    )
    recipe_two = _recipe(
        "legacy-v1:two",
        "Receita dois",
        [
            (missing_a, Decimal(30), "ml"),
            (missing_b, Decimal(2), "un"),
        ],
    )

    report = analyze_ingredient_readiness([recipe_one, recipe_two])
    azeite = next(item for item in report.priorities if item.ingredient_name == "Azeite")
    ovos = next(item for item in report.priorities if item.ingredient_name == "Ovos")

    assert azeite.blocker_type == BLOCKER_MISSING_COMPOSITION
    assert azeite.affected_recipe_count == 2
    assert azeite.occurrence_count == 2
    assert azeite.sole_blocker_recipe_count == 1
    assert ovos.affected_recipe_count == 1
    assert ovos.sole_blocker_recipe_count == 0
