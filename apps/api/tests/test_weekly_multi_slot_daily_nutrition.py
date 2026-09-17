import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.schemas.meal_plan_fit import (
    MealPlanFitCandidateRead,
    MealPlanFitRead,
    MealPlanFitRuleRead,
)
from app.services.meal_recommendation import CandidateEvaluation, MealCandidate
from app.services.serving_nutrition import NutritionSnapshot
from app.services.weekly_multi_slot_planning import (
    WeeklyMultiSlotPlanningError,
    WeeklyPlanningCandidate,
    WeeklyPlanningSlot,
    optimize_weekly_slots,
)

PERSON_ID = uuid.uuid4()
MONDAY = date(2026, 9, 14)


def _daily_rule(
    *,
    observed: str,
    projected: str,
    maximum: str = "100",
    rule_id: str = "daily-protein-max",
) -> MealPlanFitRuleRead:
    return MealPlanFitRuleRead.model_construct(
        rule_id=rule_id,
        target_type="nutrient",
        target_key="protein",
        operator="max",
        scope="daily",
        status="pass",
        is_mandatory=True,
        priority=100,
        observed_value=Decimal(observed),
        observed_unit="g",
        projected_daily_value=Decimal(projected),
        target_min=None,
        target_max=Decimal(maximum),
        target_value=None,
        target_unit="g",
        score=Decimal(1),
        explanation="Candidate stays within the maximum.",
    )


def _candidate(
    key: str,
    *,
    planning_date: date,
    meal_type: str,
    score: str,
    daily_rule: MealPlanFitRuleRead,
) -> WeeklyPlanningCandidate:
    candidate = MealCandidate(
        key=key,
        name=key,
        kind="food_item",
        quantity=Decimal(100),
        quantity_unit="g",
        nutrition=NutritionSnapshot(energy_kcal=Decimal(400), nutrients={}),
        subjects=frozenset({("food", key)}),
    )
    evaluation = CandidateEvaluation(
        candidate=candidate,
        eligible=True,
        rank=None,
        score=Decimal(score),
        score_breakdown={},
        exclusion_reasons=(),
        explanation=(),
    )
    fit = MealPlanFitRead.model_construct(
        person_id=PERSON_ID,
        planning_date=planning_date,
        meal_type=meal_type,
        candidate=MealPlanFitCandidateRead.model_construct(key=key),
        eligible=True,
        rule_results=[daily_rule],
        guideline_results=[],
    )
    return WeeklyPlanningCandidate(evaluation=evaluation, plan_fit=fit)


def _slot(
    slot_key: str,
    *,
    planning_date: date,
    meal_type: str,
    candidates: tuple[WeeklyPlanningCandidate, ...],
) -> WeeklyPlanningSlot:
    return WeeklyPlanningSlot(
        slot_key=slot_key,
        planning_date=planning_date,
        meal_type=meal_type,
        candidates=candidates,
    )


def test_same_day_candidates_recheck_combined_mandatory_daily_maximum() -> None:
    lunch_high = _candidate(
        "lunch-high",
        planning_date=MONDAY,
        meal_type="lunch",
        score="1.0000",
        daily_rule=_daily_rule(observed="40", projected="70"),
    )
    lunch_low = _candidate(
        "lunch-low",
        planning_date=MONDAY,
        meal_type="lunch",
        score="0.7000",
        daily_rule=_daily_rule(observed="20", projected="50"),
    )
    dinner_high = _candidate(
        "dinner-high",
        planning_date=MONDAY,
        meal_type="dinner",
        score="1.0000",
        daily_rule=_daily_rule(observed="40", projected="70"),
    )
    dinner_low = _candidate(
        "dinner-low",
        planning_date=MONDAY,
        meal_type="dinner",
        score="0.7000",
        daily_rule=_daily_rule(observed="20", projected="50"),
    )

    result = optimize_weekly_slots(
        (
            _slot(
                "monday:lunch",
                planning_date=MONDAY,
                meal_type="lunch",
                candidates=(lunch_high, lunch_low),
            ),
            _slot(
                "monday:dinner",
                planning_date=MONDAY,
                meal_type="dinner",
                candidates=(dinner_high, dinner_low),
            ),
        )
    )

    assert result.evaluated_combinations == 4
    assert result.rejected_by_mandatory_daily_limit == 1
    assert result.selected_plan is not None
    selected = {
        choice.candidate.evaluation.candidate.key for choice in result.selected_plan.choices
    }
    assert selected != {"lunch-high", "dinner-high"}
    assert len(selected & {"lunch-high", "dinner-high"}) == 1


def test_daily_limits_are_coupled_per_date_not_across_the_week() -> None:
    tuesday = MONDAY + timedelta(days=1)
    monday = _candidate(
        "monday-high",
        planning_date=MONDAY,
        meal_type="lunch",
        score="1.0000",
        daily_rule=_daily_rule(observed="40", projected="70"),
    )
    tuesday_candidate = _candidate(
        "tuesday-high",
        planning_date=tuesday,
        meal_type="lunch",
        score="1.0000",
        daily_rule=_daily_rule(observed="40", projected="70"),
    )

    result = optimize_weekly_slots(
        (
            _slot(
                "monday:lunch",
                planning_date=MONDAY,
                meal_type="lunch",
                candidates=(monday,),
            ),
            _slot(
                "tuesday:lunch",
                planning_date=tuesday,
                meal_type="lunch",
                candidates=(tuesday_candidate,),
            ),
        )
    )

    assert result.selected_plan is not None
    assert result.rejected_by_mandatory_daily_limit == 0
    assert [
        choice.candidate.evaluation.candidate.key for choice in result.selected_plan.choices
    ] == ["monday-high", "tuesday-high"]


def test_daily_coupling_rejects_inconsistent_daily_state_baselines() -> None:
    lunch = _candidate(
        "lunch",
        planning_date=MONDAY,
        meal_type="lunch",
        score="1.0000",
        daily_rule=_daily_rule(observed="40", projected="70"),
    )
    dinner = _candidate(
        "dinner",
        planning_date=MONDAY,
        meal_type="dinner",
        score="1.0000",
        daily_rule=_daily_rule(observed="40", projected="80"),
    )

    with pytest.raises(WeeklyMultiSlotPlanningError, match="DailyNutritionState baseline"):
        optimize_weekly_slots(
            (
                _slot(
                    "monday:lunch",
                    planning_date=MONDAY,
                    meal_type="lunch",
                    candidates=(lunch,),
                ),
                _slot(
                    "monday:dinner",
                    planning_date=MONDAY,
                    meal_type="dinner",
                    candidates=(dinner,),
                ),
            )
        )
