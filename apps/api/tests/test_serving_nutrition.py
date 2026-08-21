from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.models.family import Family
from app.models.food_catalog import (
    FoodCompositionSnapshot,
    FoodItem,
    FoodNutrientComponent,
    Recipe,
    RecipeCompositionSnapshot,
    RecipeNutrientComponent,
)
from app.models.meal import MealEvent, MealParticipant, Serving
from app.models.person import Person
from app.services.serving_nutrition import (
    CatalogReferenceMismatchError,
    UnsupportedUnitConversionError,
    calculate_serving_nutrition,
)


def _meal_participant(family: Family, person: Person) -> MealParticipant:
    meal_event = MealEvent(
        family=family,
        meal_type="dinner",
        title="Nutrition calculation test",
        scheduled_at=datetime(2026, 8, 21, 19, 30, tzinfo=UTC),
        timezone="Europe/Lisbon",
    )
    return MealParticipant(meal_event=meal_event, person=person)


def test_recipe_serving_nutrition_is_scaled_and_provenance_is_preserved(
    db_session: Session,
) -> None:
    family = Family(name="Serving Nutrition Family", timezone="Europe/Lisbon")
    person = Person(
        family=family,
        first_name="Nutrition",
        last_name="Tester",
        birth_date=date(1990, 1, 1),
        preferred_locale="pt-PT",
        timezone="Europe/Lisbon",
    )
    recipe = Recipe(
        family=family,
        recipe_key="family:bolognese",
        name="Spaghetti bolognese",
        yield_quantity=Decimal("1000.0000"),
        yield_unit="g",
        source="user",
    )
    composition = RecipeCompositionSnapshot(
        recipe=recipe,
        reference_quantity=Decimal("1000.0000"),
        reference_unit="g",
        energy_kcal=Decimal("2100.0000"),
        composition_version="recipe-v1",
        calculation_version="recipe-calc-v1",
        nutrients=[
            RecipeNutrientComponent(
                nutrient_key="protein",
                value=Decimal("140.0000"),
                unit="g",
            )
        ],
    )
    serving = Serving(
        meal_participant=_meal_participant(family, person),
        recipe=recipe,
        item_type="recipe",
        item_key=recipe.recipe_key,
        item_name=recipe.name,
        quantity_planned=Decimal("0.3500"),
        quantity_served=Decimal("0.3300"),
        quantity_consumed=Decimal("0.3000"),
        quantity_unit="kg",
    )

    calculate_serving_nutrition(serving, composition)
    db_session.add(family)
    db_session.flush()

    assert serving.energy_planned_kcal == Decimal("735.00")
    assert serving.energy_served_kcal == Decimal("693.00")
    assert serving.energy_consumed_kcal == Decimal("630.00")
    assert len(serving.nutrition_components) == 1
    protein = serving.nutrition_components[0]
    assert protein.nutrient_key == "protein"
    assert protein.planned_value == Decimal("49.0000")
    assert protein.served_value == Decimal("46.2000")
    assert protein.consumed_value == Decimal("42.0000")
    assert serving.recipe_composition_snapshot_id == composition.id
    assert serving.food_composition_snapshot_id is None
    assert serving.nutrition_source == "catalog"
    assert serving.nutrition_calculation_version == "serving-nutrition-v1"


def test_serving_nutrition_rejects_unsafe_cross_dimension_conversion() -> None:
    food = FoodItem(
        catalog_key="global:milk",
        name="Milk",
        food_kind="beverage",
        source="system",
    )
    composition = FoodCompositionSnapshot(
        food_item=food,
        reference_quantity=Decimal("100.0000"),
        reference_unit="ml",
        energy_kcal=Decimal("60.0000"),
        data_version="v1",
        source="system",
        effective_at=datetime(2026, 8, 21, tzinfo=UTC),
        nutrients=[
            FoodNutrientComponent(
                nutrient_key="protein",
                value=Decimal("3.2000"),
                unit="g",
            )
        ],
    )
    serving = Serving(
        food_item=food,
        item_type="food",
        item_key=food.catalog_key,
        item_name=food.name,
        quantity_planned=Decimal("100.0000"),
        quantity_unit="g",
    )

    with pytest.raises(UnsupportedUnitConversionError):
        calculate_serving_nutrition(serving, composition)

    assert serving.energy_planned_kcal is None
    assert serving.food_composition_snapshot is None
    assert serving.nutrition_components == []


def test_serving_nutrition_rejects_catalog_reference_mismatch() -> None:
    food = FoodItem(
        catalog_key="global:rice",
        name="Rice",
        food_kind="ingredient",
        source="system",
    )
    recipe = Recipe(
        recipe_key="global:risotto",
        name="Risotto",
        source="system",
    )
    composition = RecipeCompositionSnapshot(
        recipe=recipe,
        reference_quantity=Decimal("100.0000"),
        reference_unit="g",
        energy_kcal=Decimal("180.0000"),
        composition_version="v1",
        calculation_version="recipe-v1",
    )
    serving = Serving(
        food_item=food,
        item_type="food",
        item_key=food.catalog_key,
        item_name=food.name,
        quantity_planned=Decimal("100.0000"),
        quantity_unit="g",
    )

    with pytest.raises(CatalogReferenceMismatchError):
        calculate_serving_nutrition(serving, composition)
