import uuid
from datetime import date, timedelta
from decimal import Decimal

from app.models.person import Person
from app.schemas.meal_plan_fit import (
    MealPlanFitCandidateRead,
    MealPlanFitGuidelineRead,
    MealPlanFitRead,
)
from app.services.meal_recommendation import CandidateEvaluation, MealCandidate
from app.services.serving_nutrition import NutritionSnapshot
from app.services.shared_family_meal import (
    SharedMealCandidateEvaluation,
    SharedMealParticipantEvaluation,
    SharedMealPortion,
)
from app.services.shared_weekly_multi_slot_planning import (
    SharedWeeklyPlanningCandidate,
    SharedWeeklyPlanningSlot,
)
from app.services.shared_weekly_search import optimize_shared_weekly_slots_scalable

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


def _fit(
    person_id: uuid.UUID,
    key: str,
    *,
    planning_date: date,
    maximum_guideline_id: uuid.UUID | None = None,
    maximum: int | None = None,
    matches: bool | None = None,
) -> MealPlanFitRead:
    guidelines = []
    if maximum_guideline_id is not None:
        guidelines.append(
            MealPlanFitGuidelineRead.model_construct(
                guideline_id=maximum_guideline_id,
                guideline_type="frequency",
                period="week",
                minimum_occurrences=None,
                maximum_occurrences=maximum,
                current_occurrences=0,
                counts_are_lower_bound=False,
                unclassified_meal_count=0,
                candidate_matches=matches,
                is_mandatory=True,
                status="pass" if matches is not None else "unknown",
            )
        )
    return MealPlanFitRead.model_construct(
        person_id=person_id,
        planning_date=planning_date,
        meal_type="lunch",
        candidate=MealPlanFitCandidateRead.model_construct(key=key),
        eligible=True,
        rule_results=[],
        guideline_results=guidelines,
    )


def _candidate(
    key: str,
    *,
    planning_date: date,
    score: str,
    maximum_guideline_id: uuid.UUID | None = None,
    maximum: int | None = None,
    matches: bool | None = None,
) -> SharedWeeklyPlanningCandidate:
    candidate = _meal_candidate(key)
    score_value = Decimal(score)
    participants = tuple(
        SharedMealParticipantEvaluation(
            person=person,
            portion=SharedMealPortion(
                person_id=person_id,
                quantity=Decimal(100),
                quantity_unit="g",
            ),
            evaluation=CandidateEvaluation(
                candidate=candidate,
                eligible=True,
                rank=None,
                score=score_value,
                score_breakdown={},
                exclusion_reasons=(),
                explanation=(),
            ),
        )
        for person_id, person in ((ANA_ID, ANA), (BRUNO_ID, BRUNO))
    )
    evaluation = SharedMealCandidateEvaluation(
        candidate_key=key,
        candidate_name=key,
        candidate_kind="food_item",
        eligible=True,
        rank=None,
        minimum_score=score_value,
        average_score=score_value,
        participant_evaluations=participants,
        exclusion_reasons=(),
    )
    return SharedWeeklyPlanningCandidate(
        evaluation=evaluation,
        plan_fits=tuple(
            _fit(
                person_id,
                key,
                planning_date=planning_date,
                maximum_guideline_id=maximum_guideline_id if person_id == ANA_ID else None,
                maximum=maximum,
                matches=matches if person_id == ANA_ID else None,
            )
            for person_id in (ANA_ID, BRUNO_ID)
        ),
    )


def _slots(count: int, *, constrained: bool = False) -> tuple[SharedWeeklyPlanningSlot, ...]:
    maximum_guideline_id = uuid.uuid4() if constrained else None
    result = []
    for offset in range(count):
        planning_date = MONDAY + timedelta(days=offset % 7)
        preferred = _candidate(
            f"preferred:{offset}",
            planning_date=planning_date,
            score="1.0",
            maximum_guideline_id=maximum_guideline_id,
            maximum=1 if constrained else None,
            matches=True if constrained else None,
        )
        alternative = _candidate(
            f"alternative:{offset}",
            planning_date=planning_date,
            score="0.8",
            maximum_guideline_id=maximum_guideline_id,
            maximum=1 if constrained else None,
            matches=False if constrained else None,
        )
        result.append(
            SharedWeeklyPlanningSlot(
                slot_key=f"lunch:{offset}",
                planning_date=planning_date,
                meal_type="lunch",
                candidates=(preferred, alternative),
            )
        )
    return tuple(result)


def test_small_search_space_preserves_exact_search() -> None:
    result = optimize_shared_weekly_slots_scalable(_slots(2), max_combinations=10)

    assert result.search_strategy == "exact"
    assert result.search_space_size == 4
    assert result.search_truncated is False
    assert result.evaluated_combinations == 4
    assert result.selected_plan is not None


def test_large_search_space_uses_bounded_deterministic_search() -> None:
    result = optimize_shared_weekly_slots_scalable(_slots(7), max_combinations=35)

    assert result.search_strategy == "bounded"
    assert result.search_space_size == 128
    assert result.search_truncated is True
    assert result.evaluated_combinations <= 35
    assert result.selected_plan is not None
    assert len(result.selected_plan.choices) == 7


def test_bounded_search_avoids_repeating_near_equivalent_favorite() -> None:
    slots = []
    for offset in range(6):
        planning_date = MONDAY + timedelta(days=offset)
        favorite = _candidate(
            "favorite",
            planning_date=planning_date,
            score="1.0",
        )
        alternative = _candidate(
            f"alternative:{offset}",
            planning_date=planning_date,
            score="0.9",
        )
        slots.append(
            SharedWeeklyPlanningSlot(
                slot_key=f"dinner:{offset}",
                planning_date=planning_date,
                meal_type="lunch",
                candidates=(favorite, alternative),
            )
        )

    result = optimize_shared_weekly_slots_scalable(
        tuple(slots),
        max_combinations=len(slots),
    )

    assert result.search_strategy == "bounded"
    assert result.search_truncated is True
    assert result.selected_plan is not None
    selected = [
        choice.candidate.evaluation.candidate_key
        for choice in result.selected_plan.choices
    ]
    assert selected.count("favorite") == 1
    assert result.selected_plan.repeated_candidate_count == 0


def test_bounded_search_keeps_person_weekly_maximum_as_hard_gate() -> None:
    result = optimize_shared_weekly_slots_scalable(
        _slots(7, constrained=True),
        max_combinations=49,
    )

    assert result.search_strategy == "bounded"
    assert result.selected_plan is not None
    selected = [
        choice.candidate.evaluation.candidate_key
        for choice in result.selected_plan.choices
        if choice.candidate.evaluation.candidate_key.startswith("preferred:")
    ]
    assert len(selected) <= 1
    assert result.rejected_by_person_weekly_maximum > 0
