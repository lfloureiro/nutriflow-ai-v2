from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.family import Family
from app.models.food_catalog import (
    FoodCompositionSnapshot,
    FoodItem,
    FoodNutrientComponent,
    Recipe,
    RecipeCompositionSnapshot,
    RecipeIngredient,
    RecipeNutrientComponent,
)
from app.models.meal import MealEvent, MealParticipant, Serving
from app.models.person import Person


def test_food_catalog_recipe_composition_and_serving_links(db_session: Session) -> None:
    family = Family(name="Food Catalog Test Family", timezone="Europe/Lisbon")
    person = Person(
        family=family,
        first_name="Catalog",
        last_name="Tester",
        birth_date=date(1990, 1, 1),
        preferred_locale="pt-PT",
        timezone="Europe/Lisbon",
    )

    pasta = FoodItem(
        family=family,
        catalog_key="family:pasta:dry",
        name="Dry pasta",
        food_kind="ingredient",
        source="user",
    )
    pasta_v1 = FoodCompositionSnapshot(
        food_item=pasta,
        reference_quantity=Decimal("100.0000"),
        reference_unit="g",
        energy_kcal=Decimal("350.0000"),
        data_version="label-v1",
        source="label",
        effective_at=datetime(2026, 8, 1, tzinfo=UTC),
    )
    pasta_v1.nutrients.extend(
        [
            FoodNutrientComponent(
                nutrient_key="protein",
                value=Decimal("12.0000"),
                unit="g",
            ),
            FoodNutrientComponent(
                nutrient_key="carbohydrate",
                value=Decimal("72.0000"),
                unit="g",
            ),
        ]
    )
    pasta_v2 = FoodCompositionSnapshot(
        food_item=pasta,
        reference_quantity=Decimal("100.0000"),
        reference_unit="g",
        energy_kcal=Decimal("348.0000"),
        data_version="label-v2",
        source="label",
        effective_at=datetime(2026, 8, 20, tzinfo=UTC),
    )
    pasta_v2.nutrients.append(
        FoodNutrientComponent(
            nutrient_key="protein",
            value=Decimal("12.4000"),
            unit="g",
        )
    )

    beef = FoodItem(
        family=family,
        catalog_key="family:beef:minced",
        name="Minced beef",
        food_kind="ingredient",
        source="user",
    )
    beef.compositions.append(
        FoodCompositionSnapshot(
            reference_quantity=Decimal("100.0000"),
            reference_unit="g",
            energy_kcal=Decimal("250.0000"),
            data_version="manual-v1",
            source="manual",
            effective_at=datetime(2026, 8, 20, tzinfo=UTC),
            nutrients=[
                FoodNutrientComponent(
                    nutrient_key="protein",
                    value=Decimal("26.0000"),
                    unit="g",
                )
            ],
        )
    )

    recipe = Recipe(
        family=family,
        recipe_key="family:spaghetti-bolognese",
        name="Spaghetti bolognese",
        yield_quantity=Decimal("1000.0000"),
        yield_unit="g",
        serving_count=Decimal("4.00"),
        source="user",
    )
    recipe.ingredients.extend(
        [
            RecipeIngredient(
                food_item=pasta,
                quantity=Decimal("400.0000"),
                unit="g",
                sort_order=0,
            ),
            RecipeIngredient(
                food_item=beef,
                quantity=Decimal("350.0000"),
                unit="g",
                sort_order=1,
            ),
        ]
    )
    recipe_composition = RecipeCompositionSnapshot(
        recipe=recipe,
        reference_quantity=Decimal("1000.0000"),
        reference_unit="g",
        energy_kcal=Decimal("2100.0000"),
        composition_version="ingredients-2026-08-20",
        calculation_version="recipe-calc-v1",
        calculation_inputs={
            "food_composition_versions": ["label-v2", "manual-v1"],
        },
    )
    recipe_composition.nutrients.append(
        RecipeNutrientComponent(
            nutrient_key="protein",
            value=Decimal("140.0000"),
            unit="g",
        )
    )

    meal_event = MealEvent(
        family=family,
        meal_type="dinner",
        title="Family dinner",
        scheduled_at=datetime(2026, 8, 21, 19, 30, tzinfo=UTC),
        timezone="Europe/Lisbon",
    )
    participant = MealParticipant(meal_event=meal_event, person=person)
    serving = Serving(
        meal_participant=participant,
        recipe=recipe,
        item_type="recipe",
        item_key=recipe.recipe_key,
        item_name=recipe.name,
        quantity_planned=Decimal("350.0000"),
        quantity_unit="g",
        energy_planned_kcal=Decimal("735.00"),
        nutrition_source="catalog",
    )

    db_session.add(family)
    db_session.flush()

    assert pasta.id is not None
    assert recipe.id is not None
    assert serving.id is not None
    assert len(pasta.compositions) == 2
    assert pasta.compositions[0].data_version == "label-v1"
    assert pasta.compositions[1].data_version == "label-v2"
    assert recipe.ingredients[0].food_item is pasta
    assert recipe.ingredients[1].food_item is beef
    assert recipe.compositions[0].composition_version == "ingredients-2026-08-20"
    assert recipe.compositions[0].nutrients[0].nutrient_key == "protein"
    assert serving.recipe_id == recipe.id
    assert serving.food_item_id is None
    assert serving.item_key == "family:spaghetti-bolognese"
