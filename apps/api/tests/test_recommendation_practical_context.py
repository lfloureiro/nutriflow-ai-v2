from datetime import UTC, date, datetime, time
from decimal import Decimal

import pytest

from app.models.daily_nutrition_state import DailyNutritionState
from app.models.food_catalog import FoodCompositionSnapshot, FoodItem
from app.models.schedule_entry import ScheduleEntry
from app.services.meal_recommendation import build_food_candidate
from app.services.recommendation_practical_context import (
    CandidatePracticalProfile,
    PracticalMealContext,
    UnsupportedRecurrenceRuleError,
    evaluate_schedule_context,
    recommend_meals_with_practical_context,
)


def _daily_state() -> DailyNutritionState:
    return DailyNutritionState(
        state_date=date(2026, 8, 21),
        timezone="Europe/Lisbon",
        energy_consumed_kcal=Decimal("900.00"),
        energy_planned_kcal=Decimal("300.00"),
        energy_remaining_min_kcal=Decimal("500.00"),
        energy_remaining_max_kcal=Decimal("800.00"),
        calculation_version="daily-nutrition-v1",
    )


def _candidate(key: str, name: str):
    item = FoodItem(
        catalog_key=key,
        name=name,
        food_kind="dish",
        source="test",
    )
    composition = FoodCompositionSnapshot(
        food_item=item,
        reference_quantity=Decimal("100.0000"),
        reference_unit="g",
        energy_kcal=Decimal("500.0000"),
        data_version="test-v1",
        source="test",
        effective_at=datetime(2026, 8, 21, tzinfo=UTC),
    )
    return build_food_candidate(
        composition,
        quantity=Decimal("100.0000"),
        quantity_unit="g",
    )


def _recommend(
    *,
    candidates,
    context: PracticalMealContext,
    profiles: tuple[CandidatePracticalProfile, ...] = (),
):
    return recommend_meals_with_practical_context(
        daily_state=_daily_state(),
        candidates=candidates,
        preferences=[],
        adverse_reactions=[],
        constraints=[],
        planning_date=date(2026, 8, 21),
        practical_context=context,
        practical_profiles=profiles,
    )


def test_one_off_unavailable_overrides_recurring_preferred_window() -> None:
    candidate = _candidate("food:lunch", "Lunch")
    scheduled_at = datetime(2026, 8, 21, 12, 30, tzinfo=UTC)
    recurring = ScheduleEntry(
        entry_type="recurring",
        event_type="meal_window",
        availability_effect="preferred",
        local_start_time=time(12, 0),
        local_end_time=time(14, 0),
        recurrence_rule="FREQ=WEEKLY;BYDAY=FR",
        valid_from=date(2026, 8, 1),
        timezone="UTC",
    )
    exception = ScheduleEntry(
        entry_type="one_off",
        event_type="work",
        availability_effect="unavailable",
        starts_at=datetime(2026, 8, 21, 12, 0, tzinfo=UTC),
        ends_at=datetime(2026, 8, 21, 13, 0, tzinfo=UTC),
        timezone="UTC",
    )

    result = _recommend(
        candidates=[candidate],
        context=PracticalMealContext(
            scheduled_at=scheduled_at,
            schedule_entries=(recurring, exception),
        ),
    )

    assert result.eligible == ()
    assert result.evaluations[0].exclusion_reasons == ("schedule_unavailable",)


def test_weekly_preferred_window_is_explained_on_eligible_candidate() -> None:
    candidate = _candidate("food:lunch", "Lunch")
    recurring = ScheduleEntry(
        entry_type="recurring",
        event_type="meal_window",
        availability_effect="preferred",
        local_start_time=time(12, 0),
        local_end_time=time(14, 0),
        recurrence_rule="RRULE:FREQ=WEEKLY;BYDAY=FR",
        valid_from=date(2026, 8, 1),
        timezone="UTC",
    )

    result = _recommend(
        candidates=[candidate],
        context=PracticalMealContext(
            scheduled_at=datetime(2026, 8, 21, 12, 30, tzinfo=UTC),
            schedule_entries=(recurring,),
        ),
    )

    assert result.eligible[0].candidate.key == "food:lunch"
    assert "schedule_preferred_window" in result.eligible[0].explanation


def test_schedule_location_can_exclude_candidate_not_available_there() -> None:
    candidate = _candidate("food:home-meal", "Home meal")
    office_entry = ScheduleEntry(
        entry_type="one_off",
        event_type="work",
        availability_effect="neutral",
        starts_at=datetime(2026, 8, 21, 12, 0, tzinfo=UTC),
        ends_at=datetime(2026, 8, 21, 14, 0, tzinfo=UTC),
        timezone="UTC",
        location="Office",
    )

    result = _recommend(
        candidates=[candidate],
        context=PracticalMealContext(
            scheduled_at=datetime(2026, 8, 21, 12, 30, tzinfo=UTC),
            schedule_entries=(office_entry,),
        ),
        profiles=(
            CandidatePracticalProfile(
                candidate_key="food:home-meal",
                available_locations=frozenset({"Home"}),
            ),
        ),
    )

    assert result.eligible == ()
    assert result.evaluations[0].exclusion_reasons == (
        "candidate_unavailable_at_location:Office",
    )


def test_preparation_window_and_kitchen_requirements_filter_candidates() -> None:
    quick = _candidate("food:quick", "Quick meal")
    slow = _candidate("food:slow", "Slow meal")
    context = PracticalMealContext(
        scheduled_at=datetime(2026, 8, 21, 12, 30, tzinfo=UTC),
        available_minutes=15,
        has_kitchen=False,
    )

    result = _recommend(
        candidates=[slow, quick],
        context=context,
        profiles=(
            CandidatePracticalProfile(
                candidate_key="food:quick",
                preparation_minutes=10,
                requires_kitchen=False,
            ),
            CandidatePracticalProfile(
                candidate_key="food:slow",
                preparation_minutes=30,
                requires_kitchen=True,
            ),
        ),
    )

    assert result.eligible[0].candidate.key == "food:quick"
    excluded = next(
        evaluation for evaluation in result.evaluations if evaluation.candidate.key == "food:slow"
    )
    assert excluded.exclusion_reasons == (
        "kitchen_required",
        "preparation_time_exceeds_available_window",
    )


def test_unsupported_recurrence_rule_is_not_silently_ignored() -> None:
    entry = ScheduleEntry(
        entry_type="recurring",
        event_type="meal_window",
        availability_effect="preferred",
        local_start_time=time(12, 0),
        local_end_time=time(14, 0),
        recurrence_rule="FREQ=MONTHLY;BYDAY=FR",
        valid_from=date(2026, 8, 1),
        timezone="UTC",
    )

    with pytest.raises(UnsupportedRecurrenceRuleError, match="DAILY and WEEKLY"):
        evaluate_schedule_context(
            PracticalMealContext(
                scheduled_at=datetime(2026, 8, 21, 12, 30, tzinfo=UTC),
                schedule_entries=(entry,),
            )
        )
