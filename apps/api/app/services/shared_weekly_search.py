import uuid
from collections import Counter
from dataclasses import dataclass
from decimal import Decimal
from math import prod

from app.services.shared_weekly_multi_slot_planning import (
    ENGINE_VERSION as EXACT_ENGINE_VERSION,
)
from app.services.shared_weekly_multi_slot_planning import (
    EXACT_REPEAT_SCORE_PENALTY,
    SharedWeeklyMultiSlotPlanningError,
    SharedWeeklyMultiSlotPlanningResult,
    SharedWeeklyPlanChoice,
    SharedWeeklyPlanEvaluation,
    SharedWeeklyPlanningCandidate,
    SharedWeeklyPlanningSlot,
    _evaluate_choices,
    _normalize_slots,
    _ranking_key,
    optimize_shared_weekly_slots,
)
from app.services.weekly_multi_slot_planning import DEFAULT_MAX_COMBINATIONS

ENGINE_VERSION = "shared-weekly-search-v1"


@dataclass(frozen=True)
class SharedWeeklySearchResult:
    engine_version: str
    family_id: uuid.UUID
    participant_ids: tuple[uuid.UUID, ...]
    selected_plan: SharedWeeklyPlanEvaluation | None
    evaluated_combinations: int
    feasible_combinations: int
    rejected_by_person_weekly_maximum: int
    rejected_by_person_daily_limit: int
    search_strategy: str
    search_space_size: int
    search_truncated: bool


def _candidate_hint_key(
    candidate: SharedWeeklyPlanningCandidate,
    *,
    previous_candidate_counts: dict[str, int] | None = None,
) -> tuple[object, ...]:
    evaluation = candidate.evaluation
    rank = evaluation.rank if evaluation.rank is not None else 1_000_000
    repeat_count = (
        0
        if previous_candidate_counts is None
        else previous_candidate_counts.get(evaluation.candidate_key, 0)
    )
    repeat_penalty = EXACT_REPEAT_SCORE_PENALTY * repeat_count
    minimum_score = (evaluation.minimum_score or Decimal(0)) - repeat_penalty
    average_score = (evaluation.average_score or Decimal(0)) - repeat_penalty
    return (
        -evaluation.weekly_mandatory_support_participants,
        -evaluation.weekly_mandatory_support_total,
        -evaluation.weekly_advisory_support_participants,
        -evaluation.weekly_advisory_support_total,
        -minimum_score,
        -average_score,
        repeat_count,
        rank,
        candidate.selection_key,
    )


def _result_from_exact(
    result: SharedWeeklyMultiSlotPlanningResult,
    *,
    search_space_size: int,
) -> SharedWeeklySearchResult:
    return SharedWeeklySearchResult(
        engine_version=EXACT_ENGINE_VERSION,
        family_id=result.family_id,
        participant_ids=result.participant_ids,
        selected_plan=result.selected_plan,
        evaluated_combinations=result.evaluated_combinations,
        feasible_combinations=result.feasible_combinations,
        rejected_by_person_weekly_maximum=result.rejected_by_person_weekly_maximum,
        rejected_by_person_daily_limit=result.rejected_by_person_daily_limit,
        search_strategy="exact",
        search_space_size=search_space_size,
        search_truncated=False,
    )


def optimize_shared_weekly_slots_scalable(
    slots: tuple[SharedWeeklyPlanningSlot, ...],
    *,
    max_combinations: int = DEFAULT_MAX_COMBINATIONS,
) -> SharedWeeklySearchResult:
    """Optimize shared weekly slots with exact search when practical and bounded search otherwise.

    The bounded path never reimplements nutrition rules. Every partial state is evaluated
    through the existing Person-specific weekly optimizer, so mandatory weekly maxima,
    same-day daily limits and fail-closed evidence semantics remain authoritative.
    """
    if max_combinations < 1:
        raise SharedWeeklyMultiSlotPlanningError("max_combinations must be at least 1.")

    ordered_slots, participant_ids, family_id = _normalize_slots(slots)
    eligible_by_slot = tuple(
        tuple(
            candidate
            for candidate in slot.candidates
            if candidate.evaluation.eligible and all(fit.eligible for fit in candidate.plan_fits)
        )
        for slot in ordered_slots
    )
    if any(not candidates for candidates in eligible_by_slot):
        return SharedWeeklySearchResult(
            engine_version=ENGINE_VERSION,
            family_id=family_id,
            participant_ids=participant_ids,
            selected_plan=None,
            evaluated_combinations=0,
            feasible_combinations=0,
            rejected_by_person_weekly_maximum=0,
            rejected_by_person_daily_limit=0,
            search_strategy="bounded",
            search_space_size=0,
            search_truncated=False,
        )

    search_space_size = prod(len(candidates) for candidates in eligible_by_slot)
    if search_space_size <= max_combinations:
        exact = optimize_shared_weekly_slots(slots, max_combinations=max_combinations)
        return _result_from_exact(exact, search_space_size=search_space_size)

    if max_combinations < len(ordered_slots):
        raise SharedWeeklyMultiSlotPlanningError(
            "Bounded shared weekly search requires a budget at least as large as the number of slots."
        )

    beam: list[SharedWeeklyPlanEvaluation | None] = [None]
    evaluated = 0
    rejected_by_weekly_maximum = 0
    rejected_by_daily_limit = 0
    remaining_budget = max_combinations

    for index, (slot, candidates) in enumerate(zip(ordered_slots, eligible_by_slot, strict=True)):
        slots_remaining = len(ordered_slots) - index
        stage_budget = max(1, remaining_budget // slots_remaining)
        ordered_candidates = tuple(
            sorted(
                candidates,
                key=lambda candidate: _candidate_hint_key(candidate),
            )
        )

        expansions: list[tuple[tuple[object, ...], tuple[SharedWeeklyPlanChoice, ...]]] = []
        for state in beam:
            previous_choices = state.choices if state is not None else ()
            previous_key = _ranking_key(state) if state is not None else ()
            previous_candidate_counts = dict(
                Counter(
                    choice.candidate.evaluation.candidate_key
                    for choice in previous_choices
                )
            )
            for candidate in ordered_candidates:
                choice = SharedWeeklyPlanChoice(
                    slot_key=slot.slot_key,
                    planning_date=slot.planning_date,
                    meal_type=slot.meal_type,
                    candidate=candidate,
                )
                choices = (*previous_choices, choice)
                expansions.append(
                    (
                        (
                            _candidate_hint_key(
                                candidate,
                                previous_candidate_counts=previous_candidate_counts,
                            ),
                            previous_key,
                            tuple(
                                item.candidate.selection_key for item in choices
                            ),
                        ),
                        choices,
                    )
                )

        expansions.sort(key=lambda item: item[0])
        next_beam: list[SharedWeeklyPlanEvaluation] = []
        for _, choices in expansions[:stage_budget]:
            evaluated += 1
            plan, weekly_rejected, daily_rejected = _evaluate_choices(choices, participant_ids)
            if plan is None:
                rejected_by_weekly_maximum += int(weekly_rejected)
                rejected_by_daily_limit += int(daily_rejected)
                continue
            next_beam.append(plan)

        remaining_budget -= min(stage_budget, len(expansions))
        if not next_beam:
            return SharedWeeklySearchResult(
                engine_version=ENGINE_VERSION,
                family_id=family_id,
                participant_ids=participant_ids,
                selected_plan=None,
                evaluated_combinations=evaluated,
                feasible_combinations=0,
                rejected_by_person_weekly_maximum=rejected_by_weekly_maximum,
                rejected_by_person_daily_limit=rejected_by_daily_limit,
                search_strategy="bounded",
                search_space_size=search_space_size,
                search_truncated=True,
            )
        next_beam.sort(key=_ranking_key)
        beam = next_beam[:stage_budget]

    selected = min(beam, key=_ranking_key) if beam else None
    return SharedWeeklySearchResult(
        engine_version=ENGINE_VERSION,
        family_id=family_id,
        participant_ids=participant_ids,
        selected_plan=selected,
        evaluated_combinations=evaluated,
        feasible_combinations=len(beam),
        rejected_by_person_weekly_maximum=rejected_by_weekly_maximum,
        rejected_by_person_daily_limit=rejected_by_daily_limit,
        search_strategy="bounded",
        search_space_size=search_space_size,
        search_truncated=True,
    )
