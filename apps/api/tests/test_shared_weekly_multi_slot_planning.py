import uuid
from datetime import date
from decimal import Decimal

import pytest

from app.models.person import Person
from app.schemas.meal_plan_fit import (
    MealPlanFitCandidateRead,
    MealPlanFitGuidelineRead,
    MealPlanFitRead,
    MealPlanFitRuleRead,
)
from app.schemas.meal_type import MealType
from app.services.meal_recommendation import CandidateEvaluation, MealCandidate
from app.services.serving_nutrition import NutritionSnapshot
from app.services.shared_family_meal import (
    SharedMealCandidateEvaluation,
    SharedMealParticipantEvaluation,
    SharedMealPortion,
)
from app.services.shared_weekly_multi_slot_planning import (
    SharedWeeklyMultiSlotPlanningError,
    SharedWeeklyPlanningCandidate,
    SharedWeeklyPlanningSlot,
    optimize_shared_weekly_slots,
)

FAMILY_ID = uuid.uuid4()
ANA_ID = uuid.uuid4()
BRUNO_ID = uuid.uuid4()
MONDAY = date(2026, 9, 14)
ANA = Person(
    id=ANA_ID,
    family_id=FAMILY_ID,
    first_name="Ana",
    preferred_locale="pt-PT",
    timezone="Europe/Lisbon",
)
BRUNO = Person(
    id=BRUNO_ID,
    family_id=FAMILY_ID,
    first_name="Bruno",
    preferred_locale="pt-PT",
    timezone="Europe/Lisbon",
)


def _candidate(key: str) -> MealCandidate:
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
    mandatory: bool = True,
    minimum: int | None = None,
    maximum: int | None = None,
    current: int = 0,
    matches: bool | None,
    status: str,
) -> MealPlanFitGuidelineRead:
    return MealPlanFitGuidelineRead.model_construct(
        guideline_id=guideline_id,
        guideline_type="frequency",
        period="week",
        minimum_occurrences=minimum,
        maximum_occurrences=maximum,
        current_occurrences=current,
        counts_are_lower_bound=False,
        unclassified_meal_count=0,
        candidate_matches=matches,
        is_mandatory=mandatory,
        status=status,
    )


def _daily_max_rule(
    rule_id: str,
    *,
    observed: str,
    baseline: str,
    maximum: str,
) -> MealPlanFitRuleRead:
    observed_value = Decimal(observed)
    return MealPlanFitRuleRead.model_construct(
        rule_id=rule_id,
        target_type="nutrient",
        target_key="protein",
        operator="max",
        scope="daily",
        status="pass",
        is_mandatory=True,
        observed_value=observed_value,
        projected_daily_value=Decimal(baseline) + observed_value,
        target_max=Decimal(maximum),
        target_value=None,
        target_unit="g",
    )


def _fit(
    person_id: uuid.UUID,
    key: str,
    *,
    planning_date: date,
    meal_type: MealType,
    guidelines: tuple[MealPlanFitGuidelineRead, ...] = (),
    rules: tuple[MealPlanFitRuleRead, ...] = (),
) -> MealPlanFitRead:
    return MealPlanFitRead.model_construct(
        person_id=person_id,
        planning_date=planning_date,
        meal_type=meal_type,
        candidate=MealPlanFitCandidateRead.model_construct(key=key),
        eligible=True,
        rule_results=list(rules),
        guideline_results=list(guidelines),
    )


def _shared_candidate(
    key: str,
    *,
    planning_date: date,
    meal_type: MealType,
    ana_score: str,
    bruno_score: str,
    ana_guidelines: tuple[MealPlanFitGuidelineRead, ...] = (),
    bruno_guidelines: tuple[MealPlanFitGuidelineRead, ...] = (),
    ana_rules: tuple[MealPlanFitRuleRead, ...] = (),
    bruno_rules: tuple[MealPlanFitRuleRead, ...] = (),
) -> SharedWeeklyPlanningCandidate:
    scores = {ANA_ID: Decimal(ana_score), BRUNO_ID: Decimal(bruno_score)}
    people = {ANA_ID: ANA, BRUNO_ID: BRUNO}
    participant_evaluations = []
    for person_id in (ANA_ID, BRUNO_ID):
        evaluation = CandidateEvaluation(
            candidate=_candidate(key),
            eligible=True,
            rank=None,
            score=scores[person_id],
            score_breakdown={},
            exclusion_reasons=(),
            explanation=(),
        )
        participant_evaluations.append(
            SharedMealParticipantEvaluation(
                person=people[person_id],
                portion=SharedMealPortion(
                    person_id=person_id,
                    quantity=Decimal(100),
                    quantity_unit="g",
                ),
                evaluation=evaluation,
            )
        )

    score_values = tuple(scores.values())
    shared_evaluation = SharedMealCandidateEvaluation(
        candidate_key=key,
        candidate_name=key,
        candidate_kind="food_item",
        eligible=True,
        rank=None,
        minimum_score=min(score_values),
        average_score=sum(score_values, start=Decimal(0)) / Decimal(len(score_values)),
        participant_evaluations=tuple(participant_evaluations),
        exclusion_reasons=(),
    )
    return SharedWeeklyPlanningCandidate(
        evaluation=shared_evaluation,
        plan_fits=(
            _fit(
                ANA_ID,
                key,
                planning_date=planning_date,
                meal_type=meal_type,
                guidelines=ana_guidelines,
                rules=ana_rules,
            ),
            _fit(
                BRUNO_ID,
                key,
                planning_date=planning_date,
                meal_type=meal_type,
                guidelines=bruno_guidelines,
                rules=bruno_rules,
            ),
        ),
    )


def _slot(
    key: str,
    planning_date: date,
    meal_type: MealType,
    *candidates: SharedWeeklyPlanningCandidate,
) -> SharedWeeklyPlanningSlot:
    return SharedWeeklyPlanningSlot(
        slot_key=key,
        planning_date=planning_date,
        meal_type=meal_type,
        candidates=tuple(candidates),
    )


def test_shared_week_prefers_support_across_more_people_before_score() -> None:
    ana_fish = uuid.uuid4()
    bruno_beef = uuid.uuid4()
    slots = []
    for offset in (0, 1):
        planning_date = MONDAY.fromordinal(MONDAY.toordinal() + offset)
        fish = _shared_candidate(
            "fish",
            planning_date=planning_date,
            meal_type="lunch",
            ana_score="0.7000",
            bruno_score="0.7000",
            ana_guidelines=(
                _guideline(
                    ana_fish,
                    minimum=1,
                    matches=True,
                    status="support",
                ),
            ),
            bruno_guidelines=(
                _guideline(
                    bruno_beef,
                    minimum=1,
                    matches=False,
                    status="neutral",
                ),
            ),
        )
        beef = _shared_candidate(
            "beef",
            planning_date=planning_date,
            meal_type="lunch",
            ana_score="1.0000",
            bruno_score="1.0000",
            ana_guidelines=(
                _guideline(
                    ana_fish,
                    minimum=1,
                    matches=False,
                    status="neutral",
                ),
            ),
            bruno_guidelines=(
                _guideline(
                    bruno_beef,
                    minimum=1,
                    matches=True,
                    status="support",
                ),
            ),
        )
        slots.append(_slot(f"lunch:{offset}", planning_date, "lunch", fish, beef))

    result = optimize_shared_weekly_slots(tuple(slots))

    assert result.selected_plan is not None
    assert result.selected_plan.mandatory_support_participants == 2
    assert result.selected_plan.mandatory_support_total == 2
    selected = [
        choice.candidate.evaluation.candidate_key for choice in result.selected_plan.choices
    ]
    assert sorted(selected) == ["beef", "fish"]


def test_one_person_weekly_maximum_blocks_shared_combination() -> None:
    ana_fish_max = uuid.uuid4()
    bruno_fish_min = uuid.uuid4()
    slots = []
    for offset in (0, 1):
        planning_date = MONDAY.fromordinal(MONDAY.toordinal() + offset)
        fish = _shared_candidate(
            "fish",
            planning_date=planning_date,
            meal_type="lunch",
            ana_score="1.0000",
            bruno_score="1.0000",
            ana_guidelines=(
                _guideline(
                    ana_fish_max,
                    maximum=1,
                    matches=True,
                    status="pass",
                ),
            ),
            bruno_guidelines=(
                _guideline(
                    bruno_fish_min,
                    minimum=2,
                    matches=True,
                    status="support",
                ),
            ),
        )
        beef = _shared_candidate(
            "beef",
            planning_date=planning_date,
            meal_type="lunch",
            ana_score="0.5000",
            bruno_score="0.5000",
            ana_guidelines=(
                _guideline(
                    ana_fish_max,
                    maximum=1,
                    matches=False,
                    status="neutral",
                ),
            ),
            bruno_guidelines=(
                _guideline(
                    bruno_fish_min,
                    minimum=2,
                    matches=False,
                    status="neutral",
                ),
            ),
        )
        slots.append(_slot(f"lunch:{offset}", planning_date, "lunch", fish, beef))

    result = optimize_shared_weekly_slots(tuple(slots))

    assert result.rejected_by_person_weekly_maximum == 1
    assert result.selected_plan is not None
    selected = [
        choice.candidate.evaluation.candidate_key for choice in result.selected_plan.choices
    ]
    assert selected.count("fish") == 1
    assert result.selected_plan.mandatory_support_participants == 1


def test_one_person_daily_limit_blocks_same_day_shared_combination() -> None:
    rule_id = "daily-protein-max"
    planning_date = MONDAY
    slots = []
    for meal_type in ("lunch", "dinner"):
        high = _shared_candidate(
            "high",
            planning_date=planning_date,
            meal_type=meal_type,
            ana_score="1.0000",
            bruno_score="1.0000",
            ana_rules=(
                _daily_max_rule(
                    rule_id,
                    observed="50",
                    baseline="20",
                    maximum="100",
                ),
            ),
        )
        low = _shared_candidate(
            "low",
            planning_date=planning_date,
            meal_type=meal_type,
            ana_score="0.5000",
            bruno_score="0.5000",
            ana_rules=(
                _daily_max_rule(
                    rule_id,
                    observed="20",
                    baseline="20",
                    maximum="100",
                ),
            ),
        )
        slots.append(_slot(meal_type, planning_date, meal_type, high, low))

    result = optimize_shared_weekly_slots(tuple(slots))

    assert result.rejected_by_person_daily_limit == 1
    assert result.selected_plan is not None
    selected = [
        choice.candidate.evaluation.candidate_key for choice in result.selected_plan.choices
    ]
    assert selected.count("high") == 1
    assert selected.count("low") == 1


def test_equal_support_preserves_minimum_participant_fairness() -> None:
    slots = []
    for offset in (0, 1):
        planning_date = MONDAY.fromordinal(MONDAY.toordinal() + offset)
        polarizing = _shared_candidate(
            "polarizing",
            planning_date=planning_date,
            meal_type="lunch",
            ana_score="1.0000",
            bruno_score="0.4000",
        )
        balanced = _shared_candidate(
            "balanced",
            planning_date=planning_date,
            meal_type="lunch",
            ana_score="0.7000",
            bruno_score="0.7000",
        )
        slots.append(
            _slot(f"lunch:{offset}", planning_date, "lunch", polarizing, balanced)
        )

    result = optimize_shared_weekly_slots(tuple(slots))

    assert result.selected_plan is not None
    assert result.selected_plan.minimum_participant_score == Decimal("0.7000")
    assert [
        choice.candidate.evaluation.candidate_key for choice in result.selected_plan.choices
    ] == ["balanced", "balanced"]


def test_shared_week_refuses_search_space_above_explicit_limit() -> None:
    slots = []
    for offset in (0, 1):
        planning_date = MONDAY.fromordinal(MONDAY.toordinal() + offset)
        first = _shared_candidate(
            f"first:{offset}",
            planning_date=planning_date,
            meal_type="lunch",
            ana_score="1.0000",
            bruno_score="1.0000",
        )
        second = _shared_candidate(
            f"second:{offset}",
            planning_date=planning_date,
            meal_type="lunch",
            ana_score="1.0000",
            bruno_score="1.0000",
        )
        slots.append(_slot(f"lunch:{offset}", planning_date, "lunch", first, second))

    with pytest.raises(SharedWeeklyMultiSlotPlanningError, match="4 combinations"):
        optimize_shared_weekly_slots(tuple(slots), max_combinations=3)
