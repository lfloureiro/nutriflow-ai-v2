from datetime import UTC, date, datetime
from decimal import Decimal

from app.models.daily_nutrition_state import DailyNutritionState
from app.models.food_catalog import FoodCompositionSnapshot, FoodItem
from app.services.meal_energy_allocation import (
    allocate_meal_energy,
    size_candidate_for_meal,
)
from app.services.meal_recommendation import build_food_candidate


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


def _candidate(energy: str = "500.00"):
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


def test_lunch_budget_uses_explicit_daily_target_weight() -> None:
    allocation = allocate_meal_energy(_state(), meal_type="lunch")

    assert allocation.daily_target_min_kcal == Decimal("1800.00")
    assert allocation.daily_target_max_kcal == Decimal("2000.00")
    assert allocation.weight == Decimal("0.35")
    assert allocation.meal_target_min_kcal == Decimal("630.00")
    assert allocation.meal_target_max_kcal == Decimal("700.00")


def test_assumed_breakfast_is_part_of_daily_target_reconstruction() -> None:
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
    assert allocation.meal_target_min_kcal == Decimal("630.00")
    assert allocation.meal_target_max_kcal == Decimal("700.00")


def test_candidate_is_rounded_to_practical_quarter_serving() -> None:
    result = size_candidate_for_meal(
        _candidate("500.00"),
        _state(),
        meal_type="lunch",
    )

    assert result.portion_factor == Decimal("1.25")
    assert result.candidate.quantity == Decimal("1.2500")
    assert result.candidate.nutrition.energy_kcal == Decimal("625.00")


def test_portion_factor_is_bounded_for_extreme_candidates() -> None:
    small = size_candidate_for_meal(
        _candidate("100.00"),
        _state(),
        meal_type="lunch",
    )
    large = size_candidate_for_meal(
        _candidate("1800.00"),
        _state(),
        meal_type="lunch",
    )

    assert small.portion_factor == Decimal("2.00")
    assert large.portion_factor == Decimal("0.50")
