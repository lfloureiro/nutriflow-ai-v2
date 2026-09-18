import uuid
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from itertools import product
from math import prod

from app.schemas.meal_plan_fit import MealPlanFitRead
from app.schemas.meal_type import MealType
from app.services.shared_family_meal import (
    SharedMealCandidateEvaluation,
    SharedMealParticipantEvaluation,
)
from app.services.weekly_multi_slot_planning import (
    DEFAULT_MAX_COMBINATIONS,
    WeeklyMultiSlotPlanningError,
    WeeklyMultiSlotPlanningResult,
    WeeklyPlanningCandidate,
    WeeklyPlanningSlot,
    optimize_weekly_slots,
)

ENGINE_VERSION = "shared-weekly-multi-slot-v1"


class SharedWeeklyMultiSlotPlanningError(ValueError):
    pass


@dataclass(frozen=True)
class SharedWeeklyPlanningCandidate:
    evaluation: SharedMealCandidateEvaluation
    plan_fits: tuple[MealPlanFitRead, ...]
    variant_key: str | None = None

    @property
    def selection_key(self) -> str:
        return self.variant_key or self.evaluation.candidate_key


@dataclass(frozen=True)
class SharedWeeklyPlanningSlot:
    slot_key: str
    planning_date: date
    meal_type: MealType
    candidates: tuple[SharedWeeklyPlanningCandidate, ...]


@dataclass(frozen=True)
class SharedWeeklyPlanChoice:
    slot_key: str
    planning_date: date
    meal_type: MealType
    candidate: SharedWeeklyPlanningCandidate


@dataclass(frozen=True)
class SharedWeeklyPlanEvaluation:
    choices: tuple[SharedWeeklyPlanChoice, ...]
    mandatory_support_participants: int
    mandatory_support_total: int
    advisory_support_participants: int
    advisory_support_total: int
    minimum_participant_score: Decimal
    average_participant_score: Decimal
    repeated_candidate_count: int


@dataclass(frozen=True)
class SharedWeeklyMultiSlotPlanningResult:
    engine_version: str
    family_id: uuid.UUID
    participant_ids: tuple[uuid.UUID, ...]
    selected_plan: SharedWeeklyPlanEvaluation | None
    evaluated_combinations: int
    feasible_combinations: int
    rejected_by_person_weekly_maximum: int
    rejected_by_person_daily_limit: int


def _week_start(value: date) -> date:
    return value - timedelta(days=value.weekday())


def _participant_evaluations(
    evaluation: SharedMealCandidateEvaluation,
) -> dict[uuid.UUID, SharedMealParticipantEvaluation]:
    participants: dict[uuid.UUID, SharedMealParticipantEvaluation] = {}
    for participant in evaluation.participant_evaluations:
        person_id = participant.person.id
        if person_id is None or participant.person.family_id is None:
            raise SharedWeeklyMultiSlotPlanningError(
                "Shared weekly planning requires persisted Persons."
            )
        if person_id in participants:
            raise SharedWeeklyMultiSlotPlanningError(
                "A shared candidate cannot contain duplicate participant evaluations."
            )
        if participant.evaluation.candidate.key != evaluation.candidate_key:
            raise SharedWeeklyMultiSlotPlanningError(
                "Shared candidate and participant candidate keys must match."
            )
        participants[person_id] = participant
    if len(participants) < 2:
        raise SharedWeeklyMultiSlotPlanningError(
            "Shared weekly planning requires at least two participants."
        )
    return participants


def _plan_fits(candidate: SharedWeeklyPlanningCandidate) -> dict[uuid.UUID, MealPlanFitRead]:
    fits: dict[uuid.UUID, MealPlanFitRead] = {}
    for fit in candidate.plan_fits:
        if fit.person_id in fits:
            raise SharedWeeklyMultiSlotPlanningError(
                "A shared weekly candidate cannot contain duplicate Person Plan-Fit evidence."
            )
        fits[fit.person_id] = fit
    return fits


def _validate_candidate(
    slot: SharedWeeklyPlanningSlot,
    candidate: SharedWeeklyPlanningCandidate,
) -> tuple[frozenset[uuid.UUID], uuid.UUID]:
    participant_map = _participant_evaluations(candidate.evaluation)
    fit_map = _plan_fits(candidate)
    participant_ids = frozenset(participant_map)
    if frozenset(fit_map) != participant_ids:
        raise SharedWeeklyMultiSlotPlanningError(
            "Shared weekly candidates require exactly one Person-specific Plan-Fit per participant."
        )

    family_ids = {participant.person.family_id for participant in participant_map.values()}
    if len(family_ids) != 1 or None in family_ids:
        raise SharedWeeklyMultiSlotPlanningError(
            "All shared weekly participants must belong to the same Family."
        )
    family_id = next(iter(family_ids))
    if family_id is None:
        raise SharedWeeklyMultiSlotPlanningError("Shared weekly Family is unavailable.")

    for person_id, participant in participant_map.items():
        fit = fit_map[person_id]
        if fit.candidate.key != candidate.evaluation.candidate_key:
            raise SharedWeeklyMultiSlotPlanningError(
                "Shared candidate and Person-specific Plan-Fit candidate keys must match."
            )
        if fit.planning_date != slot.planning_date or fit.meal_type != slot.meal_type:
            raise SharedWeeklyMultiSlotPlanningError(
                f"Slot {slot.slot_key!r} has Person-specific Plan-Fit evidence for another slot."
            )
        if candidate.evaluation.eligible and participant.evaluation.eligible and not fit.eligible:
            raise SharedWeeklyMultiSlotPlanningError(
                "An eligible shared candidate cannot contain an ineligible Person Plan-Fit."
            )

    return participant_ids, family_id


def _normalize_slots(
    slots: tuple[SharedWeeklyPlanningSlot, ...],
) -> tuple[tuple[SharedWeeklyPlanningSlot, ...], tuple[uuid.UUID, ...], uuid.UUID]:
    if not slots:
        raise SharedWeeklyMultiSlotPlanningError("At least one shared planning slot is required.")
    slot_keys = [slot.slot_key for slot in slots]
    if any(not key.strip() for key in slot_keys):
        raise SharedWeeklyMultiSlotPlanningError("Shared planning slot keys must be non-empty.")
    if len(set(slot_keys)) != len(slot_keys):
        raise SharedWeeklyMultiSlotPlanningError("Shared planning slot keys must be unique.")

    ordered = tuple(sorted(slots, key=lambda item: (item.planning_date, item.meal_type, item.slot_key)))
    if len({_week_start(slot.planning_date) for slot in ordered}) != 1:
        raise SharedWeeklyMultiSlotPlanningError(
            "All shared planning slots must belong to the same Monday-Sunday week."
        )

    expected_participants: frozenset[uuid.UUID] | None = None
    expected_family: uuid.UUID | None = None
    for slot in ordered:
        if not slot.candidates:
            raise SharedWeeklyMultiSlotPlanningError(
                f"Shared planning slot {slot.slot_key!r} must contain at least one candidate."
            )
        selection_keys = [candidate.selection_key for candidate in slot.candidates]
        if len(set(selection_keys)) != len(selection_keys):
            raise SharedWeeklyMultiSlotPlanningError(
                f"Shared planning slot {slot.slot_key!r} contains duplicate candidate variants."
            )
        for candidate in slot.candidates:
            participant_ids, family_id = _validate_candidate(slot, candidate)
            if expected_participants is None:
                expected_participants = participant_ids
                expected_family = family_id
                continue
            if participant_ids != expected_participants:
                raise SharedWeeklyMultiSlotPlanningError(
                    "Every shared weekly candidate must contain the same participant set."
                )
            if family_id != expected_family:
                raise SharedWeeklyMultiSlotPlanningError(
                    "Every shared weekly candidate must belong to the same Family."
                )

    if expected_participants is None or expected_family is None:
        raise SharedWeeklyMultiSlotPlanningError("Shared weekly planning context is unavailable.")
    return ordered, tuple(sorted(expected_participants, key=str)), expected_family


def _person_weekly_result(
    person_id: uuid.UUID,
    choices: tuple[SharedWeeklyPlanChoice, ...],
) -> WeeklyMultiSlotPlanningResult:
    person_slots: list[WeeklyPlanningSlot] = []
    for choice in choices:
        participants = _participant_evaluations(choice.candidate.evaluation)
        fits = _plan_fits(choice.candidate)
        participant = participants[person_id]
        fit = fits[person_id]
        person_slots.append(
            WeeklyPlanningSlot(
                slot_key=choice.slot_key,
                planning_date=choice.planning_date,
                meal_type=choice.meal_type,
                candidates=(
                    WeeklyPlanningCandidate(
                        evaluation=participant.evaluation,
                        plan_fit=fit,
                    ),
                ),
            )
        )
    try:
        return optimize_weekly_slots(tuple(person_slots), max_combinations=1)
    except WeeklyMultiSlotPlanningError as exc:
        raise SharedWeeklyMultiSlotPlanningError(
            f"Person {person_id} weekly evidence is inconsistent: {exc}"
        ) from exc


def _evaluate_choices(
    choices: tuple[SharedWeeklyPlanChoice, ...],
    participant_ids: tuple[uuid.UUID, ...],
) -> tuple[SharedWeeklyPlanEvaluation | None, bool, bool]:
    person_results = tuple(_person_weekly_result(person_id, choices) for person_id in participant_ids)
    rejected_by_weekly_maximum = any(
        result.rejected_by_mandatory_weekly_maximum > 0 for result in person_results
    )
    rejected_by_daily_limit = any(
        result.rejected_by_mandatory_daily_limit > 0 for result in person_results
    )
    if any(result.selected_plan is None for result in person_results):
        return None, rejected_by_weekly_maximum, rejected_by_daily_limit

    person_plans = tuple(
        result.selected_plan for result in person_results if result.selected_plan is not None
    )
    mandatory_values = tuple(
        plan.mandatory_minimum_occurrences_supported for plan in person_plans
    )
    advisory_values = tuple(
        plan.advisory_minimum_occurrences_supported for plan in person_plans
    )
    minimum_scores = tuple(plan.minimum_score for plan in person_plans)
    average_scores = tuple(plan.average_score for plan in person_plans)
    candidate_keys = tuple(choice.candidate.evaluation.candidate_key for choice in choices)

    return (
        SharedWeeklyPlanEvaluation(
            choices=choices,
            mandatory_support_participants=sum(value > 0 for value in mandatory_values),
            mandatory_support_total=sum(mandatory_values),
            advisory_support_participants=sum(value > 0 for value in advisory_values),
            advisory_support_total=sum(advisory_values),
            minimum_participant_score=min(minimum_scores),
            average_participant_score=(
                sum(average_scores, start=Decimal(0)) / Decimal(len(average_scores))
            ),
            repeated_candidate_count=len(candidate_keys) - len(set(candidate_keys)),
        ),
        False,
        False,
    )


def _ranking_key(plan: SharedWeeklyPlanEvaluation) -> tuple[object, ...]:
    selection_keys = tuple(choice.candidate.selection_key for choice in plan.choices)
    return (
        -plan.mandatory_support_participants,
        -plan.mandatory_support_total,
        -plan.advisory_support_participants,
        -plan.advisory_support_total,
        -plan.minimum_participant_score,
        -plan.average_participant_score,
        plan.repeated_candidate_count,
        selection_keys,
    )


def optimize_shared_weekly_slots(
    slots: tuple[SharedWeeklyPlanningSlot, ...],
    *,
    max_combinations: int = DEFAULT_MAX_COMBINATIONS,
) -> SharedWeeklyMultiSlotPlanningResult:
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
        return SharedWeeklyMultiSlotPlanningResult(
            engine_version=ENGINE_VERSION,
            family_id=family_id,
            participant_ids=participant_ids,
            selected_plan=None,
            evaluated_combinations=0,
            feasible_combinations=0,
            rejected_by_person_weekly_maximum=0,
            rejected_by_person_daily_limit=0,
        )

    combination_count = prod(len(candidates) for candidates in eligible_by_slot)
    if combination_count > max_combinations:
        raise SharedWeeklyMultiSlotPlanningError(
            f"Shared weekly planning search space has {combination_count} combinations; "
            f"the deterministic limit is {max_combinations}."
        )

    feasible: list[SharedWeeklyPlanEvaluation] = []
    rejected_by_weekly_maximum = 0
    rejected_by_daily_limit = 0
    evaluated = 0
    for candidate_combination in product(*eligible_by_slot):
        evaluated += 1
        choices = tuple(
            SharedWeeklyPlanChoice(
                slot_key=slot.slot_key,
                planning_date=slot.planning_date,
                meal_type=slot.meal_type,
                candidate=candidate,
            )
            for slot, candidate in zip(ordered_slots, candidate_combination, strict=True)
        )
        plan, weekly_rejected, daily_rejected = _evaluate_choices(choices, participant_ids)
        if plan is None:
            rejected_by_weekly_maximum += int(weekly_rejected)
            rejected_by_daily_limit += int(daily_rejected)
            continue
        feasible.append(plan)

    selected = min(feasible, key=_ranking_key) if feasible else None
    return SharedWeeklyMultiSlotPlanningResult(
        engine_version=ENGINE_VERSION,
        family_id=family_id,
        participant_ids=participant_ids,
        selected_plan=selected,
        evaluated_combinations=evaluated,
        feasible_combinations=len(feasible),
        rejected_by_person_weekly_maximum=rejected_by_weekly_maximum,
        rejected_by_person_daily_limit=rejected_by_daily_limit,
    )
