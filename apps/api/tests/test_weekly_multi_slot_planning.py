import uuid
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.schemas.meal_plan_fit import (
    MealPlanFitCandidateRead,
    MealPlanFitGuidelineRead,
    MealPlanFitRead,
)
from app.schemas.nutrition_plan import (
    EffectiveNutritionGuidelineRead,
    EffectiveNutritionPlanSourceRead,
)
from app.schemas.weekly_frequency_progress import WeeklyFrequencyGuidelineProgressRead
from app.services.meal_plan_fit_weekly_frequency import _frequency_result
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


def _meal_candidate(key: str) -> MealCandidate:
    return MealCandidate(
        key=key,
        name=key,
        kind="food_item",
        quantity=Decimal(100),
        quantity_unit="g",
        nutrition=NutritionSnapshot(energy_kcal=Decimal(400), nutrients={}),
        subjects=frozenset({("food", key)}),
    )


def _guideline(
    guideline_id: uuid.UUID,
    *,
    mandatory: bool,
    minimum: int | None = None,
    maximum: int | None = None,
    current: int = 0,
    lower_bound: bool = False,
    unclassified: int = 0,
    candidate_matches: bool | None,
    status: str,
) -> MealPlanFitGuidelineRead:
    return MealPlanFitGuidelineRead.model_construct(
        guideline_id=guideline_id,
        guideline_type="frequency",
        period="week",
        minimum_occurrences=minimum,
        maximum_occurrences=maximum,
        current_occurrences=current,
        counts_are_lower_bound=lower_bound,
        unclassified_meal_count=unclassified,
        candidate_matches=candidate_matches,
        is_mandatory=mandatory,
        status=status,
    )


def _option(
    key: str,
    *,
    planning_date: date,
    score: str,
    guidelines: tuple[MealPlanFitGuidelineRead, ...] = (),
    eligible: bool = True,
) -> WeeklyPlanningCandidate:
    candidate = _meal_candidate(key)
    evaluation = CandidateEvaluation(
        candidate=candidate,
        eligible=eligible,
        rank=None,
        score=Decimal(score) if score else None,
        score_breakdown={},
        exclusion_reasons=(),
        explanation=(),
    )
    fit = MealPlanFitRead.model_construct(
        person_id=PERSON_ID,
        planning_date=planning_date,
        meal_type="lunch",
        candidate=MealPlanFitCandidateRead.model_construct(key=key),
        eligible=eligible,
        guideline_results=list(guidelines),
    )
    return WeeklyPlanningCandidate(evaluation=evaluation, plan_fit=fit)


def _slot(
    key: str,
    planning_date: date,
    *candidates: WeeklyPlanningCandidate,
) -> WeeklyPlanningSlot:
    return WeeklyPlanningSlot(
        slot_key=key,
        planning_date=planning_date,
        meal_type="lunch",
        candidates=tuple(candidates),
    )


def test_multi_slot_planner_satisfies_confirmed_mandatory_deficit_before_score() -> None:
    guideline_id = uuid.uuid4()
    slots = []
    for offset in (0, 1):
        planning_date = MONDAY.fromordinal(MONDAY.toordinal() + offset)
        fish = _option(
            f"fish:{offset}",
            planning_date=planning_date,
            score="0.7000",
            guidelines=(
                _guideline(
                    guideline_id,
                    mandatory=True,
                    minimum=3,
                    current=1,
                    candidate_matches=True,
                    status="support",
                ),
            ),
        )
        preferred = _option(
            f"preferred:{offset}",
            planning_date=planning_date,
            score="1.0000",
            guidelines=(
                _guideline(
                    guideline_id,
                    mandatory=True,
                    minimum=3,
                    current=1,
                    candidate_matches=False,
                    status="neutral",
                ),
            ),
        )
        slots.append(_slot(f"lunch:{offset}", planning_date, preferred, fish))

    result = optimize_weekly_slots(tuple(slots))

    assert result.selected_plan is not None
    assert result.selected_plan.mandatory_minimum_occurrences_supported == 2
    assert [
        choice.candidate.evaluation.candidate.key for choice in result.selected_plan.choices
    ] == ["fish:0", "fish:1"]


def test_multi_slot_support_is_capped_at_confirmed_remaining_deficit() -> None:
    guideline_id = uuid.uuid4()
    slots = []
    for offset in (0, 1, 2):
        planning_date = MONDAY.fromordinal(MONDAY.toordinal() + offset)
        fish = _option(
            f"fish:{offset}",
            planning_date=planning_date,
            score="0.8000",
            guidelines=(
                _guideline(
                    guideline_id,
                    mandatory=True,
                    minimum=2,
                    current=1,
                    candidate_matches=True,
                    status="support",
                ),
            ),
        )
        slots.append(_slot(f"lunch:{offset}", planning_date, fish))

    result = optimize_weekly_slots(tuple(slots))

    assert result.selected_plan is not None
    assert result.selected_plan.mandatory_minimum_occurrences_supported == 1


def test_multi_slot_support_respects_lower_bound_unclassified_meals() -> None:
    guideline_id = uuid.uuid4()
    slots = []
    for offset in (0, 1, 2):
        planning_date = MONDAY.fromordinal(MONDAY.toordinal() + offset)
        fish = _option(
            f"fish:{offset}",
            planning_date=planning_date,
            score="0.8000",
            guidelines=(
                _guideline(
                    guideline_id,
                    mandatory=True,
                    minimum=5,
                    current=1,
                    lower_bound=True,
                    unclassified=2,
                    candidate_matches=True,
                    status="support",
                ),
            ),
        )
        slots.append(_slot(f"lunch:{offset}", planning_date, fish))

    result = optimize_weekly_slots(tuple(slots))

    assert result.selected_plan is not None
    assert result.selected_plan.mandatory_minimum_occurrences_supported == 2


def test_combined_mandatory_weekly_maximum_rejects_individually_safe_choices() -> None:
    guideline_id = uuid.uuid4()
    slots = []
    for offset in (0, 1):
        planning_date = MONDAY.fromordinal(MONDAY.toordinal() + offset)
        fish = _option(
            f"fish:{offset}",
            planning_date=planning_date,
            score="1.0000",
            guidelines=(
                _guideline(
                    guideline_id,
                    mandatory=True,
                    maximum=1,
                    current=0,
                    candidate_matches=True,
                    status="pass",
                ),
            ),
        )
        other = _option(
            f"other:{offset}",
            planning_date=planning_date,
            score="0.5000",
            guidelines=(
                _guideline(
                    guideline_id,
                    mandatory=True,
                    maximum=1,
                    current=0,
                    candidate_matches=False,
                    status="neutral",
                ),
            ),
        )
        slots.append(_slot(f"lunch:{offset}", planning_date, fish, other))

    result = optimize_weekly_slots(tuple(slots))

    assert result.evaluated_combinations == 4
    assert result.rejected_by_mandatory_weekly_maximum == 1
    assert result.selected_plan is not None
    selected = [
        choice.candidate.plan_fit.guideline_results[0].candidate_matches
        for choice in result.selected_plan.choices
    ]
    assert selected.count(True) == 1


def test_combined_maximum_fails_closed_for_multiple_unknown_candidate_matches() -> None:
    guideline_id = uuid.uuid4()
    slots = []
    for offset in (0, 1):
        planning_date = MONDAY.fromordinal(MONDAY.toordinal() + offset)
        unknown = _option(
            f"unknown:{offset}",
            planning_date=planning_date,
            score="1.0000",
            guidelines=(
                _guideline(
                    guideline_id,
                    mandatory=True,
                    maximum=1,
                    current=0,
                    candidate_matches=None,
                    status="neutral",
                ),
            ),
        )
        known_non_match = _option(
            f"safe:{offset}",
            planning_date=planning_date,
            score="0.5000",
            guidelines=(
                _guideline(
                    guideline_id,
                    mandatory=True,
                    maximum=1,
                    current=0,
                    candidate_matches=False,
                    status="neutral",
                ),
            ),
        )
        slots.append(_slot(f"lunch:{offset}", planning_date, unknown, known_non_match))

    result = optimize_weekly_slots(tuple(slots))

    assert result.rejected_by_mandatory_weekly_maximum == 1
    assert result.selected_plan is not None
    selected = [
        choice.candidate.plan_fit.guideline_results[0].candidate_matches
        for choice in result.selected_plan.choices
    ]
    assert selected.count(None) == 1


def test_multi_slot_planner_uses_stable_tie_break_and_avoids_exact_repeat_on_tie() -> None:
    day_one = MONDAY
    day_two = MONDAY.fromordinal(MONDAY.toordinal() + 1)
    slots = (
        _slot(
            "one",
            day_one,
            _option("alpha", planning_date=day_one, score="1.0000"),
            _option("beta", planning_date=day_one, score="1.0000"),
        ),
        _slot(
            "two",
            day_two,
            _option("alpha", planning_date=day_two, score="1.0000"),
            _option("beta", planning_date=day_two, score="1.0000"),
        ),
    )

    result = optimize_weekly_slots(slots)

    assert result.selected_plan is not None
    assert result.selected_plan.repeated_candidate_count == 0
    assert [
        choice.candidate.evaluation.candidate.key for choice in result.selected_plan.choices
    ] == ["alpha", "beta"]


def test_multi_slot_planner_refuses_unbounded_search_space() -> None:
    day_one = MONDAY
    day_two = MONDAY.fromordinal(MONDAY.toordinal() + 1)
    slots = (
        _slot(
            "one",
            day_one,
            _option("a", planning_date=day_one, score="1.0000"),
            _option("b", planning_date=day_one, score="1.0000"),
        ),
        _slot(
            "two",
            day_two,
            _option("c", planning_date=day_two, score="1.0000"),
            _option("d", planning_date=day_two, score="1.0000"),
        ),
    )

    with pytest.raises(WeeklyMultiSlotPlanningError, match="4 combinations"):
        optimize_weekly_slots(slots, max_combinations=3)


def test_frequency_result_exposes_structured_match_and_unclassified_evidence() -> None:
    source = EffectiveNutritionPlanSourceRead(
        plan_id=None,
        plan_title=None,
        plan_source_type=None,
        source_name=None,
        source_reference=None,
        rule_source=None,
    )
    guideline_id = uuid.uuid4()
    guideline = EffectiveNutritionGuidelineRead(
        id=guideline_id,
        guideline_type="frequency",
        target_type="food_category",
        target_key="fish",
        description="Fish at least four times per week",
        meal_type=None,
        period="week",
        minimum_occurrences=4,
        maximum_occurrences=None,
        severity="mandatory",
        is_mandatory=True,
        priority=100,
        confirmation_status="confirmed",
        source=source,
    )
    progress = WeeklyFrequencyGuidelineProgressRead.model_construct(
        guideline_id=guideline_id,
        minimum_occurrences=4,
        maximum_occurrences=None,
        total_occurrences=1,
        unclassified_meal_count=2,
        counts_are_lower_bound=True,
        evidence_status="evaluated",
    )
    candidate = _meal_candidate("fish")
    profile = SimpleNamespace(planning_category="main", primary_protein="fish")

    result = _frequency_result(
        guideline,
        progress=progress,
        candidate=candidate,
        profile=profile,
    )

    assert result.status == "support"
    assert result.candidate_matches is True
    assert result.unclassified_meal_count == 2
    assert result.matched_by == ["primary_protein"]
