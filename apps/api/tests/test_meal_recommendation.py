from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from app.models.daily_nutrition_state import DailyNutritionState, DailyNutritionStateComponent
from app.models.food_adverse_reaction import FoodAdverseReaction
from app.models.food_catalog import (
    FoodCompositionSnapshot,
    FoodItem,
    FoodNutrientComponent,
    Recipe,
    RecipeCompositionSnapshot,
    RecipeIngredient,
)
from app.models.food_preference import FoodPreference
from app.models.nutrition_constraint import NutritionConstraint
from app.services.meal_recommendation import (
    UnsupportedMandatoryConstraintError,
    build_food_candidate,
    build_recipe_candidate,
    recommend_meals,
)


def _daily_state(*components: DailyNutritionStateComponent) -> DailyNutritionState:
    return DailyNutritionState(
        state_date=date(2026, 8, 21),
        timezone="Europe/Lisbon",
        energy_consumed_kcal=Decimal("900.00"),
        energy_planned_kcal=Decimal("300.00"),
        energy_remaining_min_kcal=Decimal("500.00"),
        energy_remaining_max_kcal=Decimal("800.00"),
        calculation_version="daily-nutrition-v1",
        components=list(components),
    )


def _food_candidate(
    *,
    key: str,
    name: str,
    energy: str,
    protein: str = "0",
    sodium: str = "0",
):
    item = FoodItem(
        catalog_key=key,
        name=name,
        food_kind="ingredient",
        source="test",
    )
    composition = FoodCompositionSnapshot(
        food_item=item,
        reference_quantity=Decimal("100.0000"),
        reference_unit="g",
        energy_kcal=Decimal(energy),
        data_version="test-v1",
        source="test",
        effective_at=datetime(2026, 8, 21, tzinfo=UTC),
        nutrients=[
            FoodNutrientComponent(
                nutrient_key="protein",
                value=Decimal(protein),
                unit="g",
            ),
            FoodNutrientComponent(
                nutrient_key="sodium",
                value=Decimal(sodium),
                unit="mg",
            ),
        ],
    )
    return build_food_candidate(
        composition,
        quantity=Decimal("100.0000"),
        quantity_unit="g",
    )


def test_mandatory_adverse_reaction_excludes_recipe_ingredient() -> None:
    peanut = FoodItem(
        catalog_key="food:peanut",
        name="Peanut",
        food_kind="ingredient",
        source="test",
    )
    rice = FoodItem(
        catalog_key="food:rice",
        name="Rice",
        food_kind="ingredient",
        source="test",
    )

    peanut_recipe = Recipe(
        recipe_key="recipe:peanut-rice",
        name="Peanut rice",
        source="test",
        ingredients=[
            RecipeIngredient(
                food_item=peanut,
                quantity=Decimal("20.0000"),
                unit="g",
                sort_order=0,
            )
        ],
    )
    safe_recipe = Recipe(
        recipe_key="recipe:plain-rice",
        name="Plain rice",
        source="test",
        ingredients=[
            RecipeIngredient(
                food_item=rice,
                quantity=Decimal("100.0000"),
                unit="g",
                sort_order=0,
            )
        ],
    )

    peanut_candidate = build_recipe_candidate(
        RecipeCompositionSnapshot(
            recipe=peanut_recipe,
            reference_quantity=Decimal("300.0000"),
            reference_unit="g",
            energy_kcal=Decimal("550.0000"),
            composition_version="test-v1",
            calculation_version="recipe-v1",
        ),
        quantity=Decimal("300.0000"),
        quantity_unit="g",
    )
    safe_candidate = build_recipe_candidate(
        RecipeCompositionSnapshot(
            recipe=safe_recipe,
            reference_quantity=Decimal("300.0000"),
            reference_unit="g",
            energy_kcal=Decimal("500.0000"),
            composition_version="test-v1",
            calculation_version="recipe-v1",
        ),
        quantity=Decimal("300.0000"),
        quantity_unit="g",
    )

    result = recommend_meals(
        daily_state=_daily_state(),
        candidates=[peanut_candidate, safe_candidate],
        preferences=[],
        adverse_reactions=[
            FoodAdverseReaction(
                reaction_type="allergy",
                subject_type="ingredient",
                subject_key="food:peanut",
                severity="severe",
                is_mandatory=True,
                source="user",
            )
        ],
        constraints=[],
        planning_date=date(2026, 8, 21),
    )

    assert result.eligible[0].candidate.key == "recipe:plain-rice"
    excluded = next(
        evaluation
        for evaluation in result.evaluations
        if evaluation.candidate.key == "recipe:peanut-rice"
    )
    assert excluded.eligible is False
    assert excluded.exclusion_reasons == ("mandatory_reaction:ingredient:food:peanut",)


def test_preferences_and_nutrient_deficit_rank_candidate() -> None:
    protein_state = DailyNutritionStateComponent(
        target_type="nutrient",
        target_key="protein",
        consumed_value=Decimal("40.0000"),
        planned_value=Decimal("10.0000"),
        remaining_min=Decimal("50.0000"),
        remaining_max=Decimal("90.0000"),
        unit="g",
    )
    high_protein = _food_candidate(
        key="food:chicken",
        name="Chicken",
        energy="550.0000",
        protein="45.0000",
    )
    low_protein = _food_candidate(
        key="food:white-rice",
        name="White rice",
        energy="550.0000",
        protein="5.0000",
    )

    result = recommend_meals(
        daily_state=_daily_state(protein_state),
        candidates=[low_protein, high_protein],
        preferences=[
            FoodPreference(
                subject_type="ingredient",
                subject_key="food:chicken",
                preference_type="like",
                intensity=5,
                source="user",
            )
        ],
        adverse_reactions=[],
        constraints=[],
        planning_date=date(2026, 8, 21),
    )

    assert result.eligible[0].candidate.key == "food:chicken"
    assert result.eligible[0].rank == 1
    assert "supports_deficit:protein" in result.eligible[0].explanation
    assert "preferred:ingredient:food:chicken" in result.eligible[0].explanation


def test_mandatory_daily_nutrient_max_excludes_candidate() -> None:
    sodium_state = DailyNutritionStateComponent(
        target_type="nutrient",
        target_key="sodium",
        consumed_value=Decimal("800.0000"),
        planned_value=Decimal("0.0000"),
        remaining_max=Decimal("200.0000"),
        unit="mg",
    )
    high_sodium = _food_candidate(
        key="food:soup",
        name="Soup",
        energy="400.0000",
        protein="15.0000",
        sodium="350.0000",
    )
    low_sodium = _food_candidate(
        key="food:salad",
        name="Salad",
        energy="350.0000",
        protein="12.0000",
        sodium="100.0000",
    )
    sodium_limit = NutritionConstraint(
        constraint_type="nutrient_limit",
        target_type="nutrient",
        target_key="sodium",
        operator="max",
        value_max=Decimal("1000.0000"),
        unit="mg",
        severity="required",
        is_mandatory=True,
        source="doctor",
    )

    result = recommend_meals(
        daily_state=_daily_state(sodium_state),
        candidates=[high_sodium, low_sodium],
        preferences=[],
        adverse_reactions=[],
        constraints=[sodium_limit],
        planning_date=date(2026, 8, 21),
    )

    assert result.eligible[0].candidate.key == "food:salad"
    excluded = next(
        evaluation
        for evaluation in result.evaluations
        if evaluation.candidate.key == "food:soup"
    )
    assert excluded.exclusion_reasons == ("mandatory_nutrient_max:sodium",)


def test_unknown_mandatory_constraint_stops_recommendation() -> None:
    candidate = _food_candidate(
        key="food:yogurt",
        name="Yogurt",
        energy="300.0000",
        protein="20.0000",
    )
    unsupported = NutritionConstraint(
        constraint_type="timing",
        target_type="meal_timing",
        target_key="after_20_00",
        operator="exclude",
        severity="required",
        is_mandatory=True,
        source="nutritionist",
    )

    with pytest.raises(UnsupportedMandatoryConstraintError):
        recommend_meals(
            daily_state=_daily_state(),
            candidates=[candidate],
            preferences=[],
            adverse_reactions=[],
            constraints=[unsupported],
            planning_date=date(2026, 8, 21),
        )
