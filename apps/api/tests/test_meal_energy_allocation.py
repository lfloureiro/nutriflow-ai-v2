from datetime import UTC, date, datetime
from decimal import Decimal

from app.models.daily_nutrition_state import DailyNutritionState
from app.models.food_catalog import (
    FoodCompositionSnapshot,
    FoodItem,
    Recipe,
    RecipeCompositionSnapshot,
)
from app.services.meal_energy_allocation import (
    allocate_meal_energy,
    size_candidate_for_meal,
)
from app.services.meal_recommendation import (
    build_food_candidate,
    build_recipe_candidate,
    recommend_meals,
)


def _state(
    *,
    consumed: str = "350.00",
    planned: str = "0.00",
    assumed: str = "0.00",
    remaining_min: str = "1450.00",
    remaining_max: str = "1650.00",
) -> DailyNutritionState:
    return DailyNutritionState(
        state_date=date(2026, 8, 23),
        timezone="Europe/Lisbon",
        energy_consumed_kcal=Decimal(consumed),
        energy_planned_kcal=Decimal(planned),
        energy_assumed_kcal=Decimal(assumed),
        energy_remaining_min_kcal=Decimal(remaining_min),
        energy_remaining_max_kcal=Decimal(remaining_max),
        calculation_version="test",
    )


def _dish_candidate(energy: str = "500.00"):
    item = FoodItem(
        catalog_key="test:meal",
        name="Test meal",
        food_kind="dish",
        source="test",
    )
    composition = FoodCompositionSnapshot(
        food_item=item,
        reference_quantity=Decimal("1.0000"),
        reference_unit="serving",
        energy_kcal=Decimal(energy),
        data_version="test-v1",
        source="test",
        effective_at=datetime(2026, 8, 23, tzinfo=UTC),
    )
    return build_food_candidate(
        composition,
        quantity=Decimal("1.0000"),
        quantity_unit="serving",
    )


def _recipe_candidate(energy: str = "500.00"):
    recipe = Recipe(
        recipe_key="test:recipe",
        name="Test recipe",
        serving_count=Decimal(1),
        source="test",
    )
    composition = RecipeCompositionSnapshot(
        recipe=recipe,
        reference_quantity=Decimal("1.0000"),
        reference_unit="serving",
        energy_kcal=Decimal(energy),
        composition_version="test-v1",
        calculation_version="test",
        computed_at=datetime(2026, 8, 23, tzinfo=UTC),
    )
    return build_recipe_candidate(
        composition,
        quantity=Decimal("1.0000"),
        quantity_unit="serving",
    )


def test_lunch_budget_redistributes_remaining_daily_energy() -> None:
    allocation = allocate_meal_energy(_state(), meal_type="lunch")

    assert allocation.daily_target_min_kcal == Decimal("1800.00")
    assert allocation.daily_target_max_kcal == Decimal("2000.00")
    assert allocation.weight == Decimal("0.35")
    assert allocation.remaining_weight == Decimal("0.75")
    assert allocation.meal_target_min_kcal == Decimal("676.67")
    assert allocation.meal_target_max_kcal == Decimal("770.00")


def test_assumed_breakfast_counts_as_spent_energy_before_redistribution() -> None:
    allocation = allocate_meal_energy(
        _state(
            consumed="0.00",
            assumed="350.00",
            remaining_min="1450.00",
            remaining_max="1650.00",
        ),
        meal_type="lunch",
    )

    assert allocation.daily_target_min_kcal == Decimal("1800.00")
    assert allocation.daily_target_max_kcal == Decimal("2000.00")
    assert allocation.meal_target_min_kcal == Decimal("676.67")
    assert allocation.meal_target_max_kcal == Decimal("770.00")


def test_skipped_breakfast_redistributes_its_budget_to_remaining_meals() -> None:
    allocation = allocate_meal_energy(
        _state(
            consumed="0.00",
            assumed="0.00",
            remaining_min="1800.00",
            remaining_max="2000.00",
        ),
        meal_type="lunch",
    )

    assert allocation.meal_target_min_kcal == Decimal("840.00")
    assert allocation.meal_target_max_kcal == Decimal("933.33")


def test_dinner_uses_the_remaining_daily_energy() -> None:
    allocation = allocate_meal_energy(
        _state(
            consumed="1200.00",
            remaining_min="600.00",
            remaining_max="800.00",
        ),
        meal_type="dinner",
    )

    assert allocation.remaining_weight == Decimal("0.30")
    assert allocation.meal_target_min_kcal == Decimal("600.00")
    assert allocation.meal_target_max_kcal == Decimal("800.00")


def test_recipe_candidate_is_rounded_to_practical_quarter_serving() -> None:
    result = size_candidate_for_meal(
        _recipe_candidate("500.00"),
        _state(),
        meal_type="lunch",
    )

    assert result.portion_factor == Decimal("1.50")
    assert result.candidate.quantity == Decimal("1.5000")
    assert result.candidate.nutrition.energy_kcal == Decimal("750.00")
    assert result.candidate.meal_energy_target_min_kcal == Decimal("676.67")
    assert result.candidate.meal_energy_target_max_kcal == Decimal("770.00")
    assert result.candidate.energy_allocation_policy == "meal-energy-allocation-v2"


def test_commercial_dish_keeps_real_serving_size() -> None:
    result = size_candidate_for_meal(
        _dish_candidate("500.00"),
        _state(),
        meal_type="lunch",
    )

    assert result.portion_factor == Decimal(1)
    assert result.candidate.quantity == Decimal("1.0000")
    assert result.candidate.nutrition.energy_kcal == Decimal("500.00")
    assert result.candidate.meal_energy_target_min_kcal == Decimal("676.67")
    assert result.candidate.meal_energy_target_max_kcal == Decimal("770.00")


def test_sized_candidate_energy_score_uses_meal_target_not_whole_day() -> None:
    state = _state()
    sized = size_candidate_for_meal(
        _recipe_candidate("500.00"),
        state,
        meal_type="lunch",
    ).candidate

    recommendation = recommend_meals(
        daily_state=state,
        candidates=[sized],
        preferences=[],
        adverse_reactions=[],
        constraints=[],
        planning_date=date(2026, 8, 23),
    )

    evaluation = recommendation.eligible[0]
    assert evaluation.score_breakdown["energy"] > Decimal("0.95")
    assert "candidate_fits_meal_energy" in evaluation.explanation


def test_recipe_portion_factor_is_bounded_for_extreme_candidates() -> None:
    small = size_candidate_for_meal(
        _recipe_candidate("100.00"),
        _state(),
        meal_type="lunch",
    )
    large = size_candidate_for_meal(
        _recipe_candidate("1800.00"),
        _state(),
        meal_type="lunch",
    )

    assert small.portion_factor == Decimal("2.00")
    assert large.portion_factor == Decimal("0.50")
