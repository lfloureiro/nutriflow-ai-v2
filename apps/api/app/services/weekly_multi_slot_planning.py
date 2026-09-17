import uuid
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from itertools import product
from math import prod

from app.schemas.meal_plan_fit import MealPlanFitGuidelineRead, MealPlanFitRead
from app.schemas.meal_type import MealType
from app.services.meal_recommendation import CandidateEvaluation

DEFAULT_MAX_COMBINATIONS = 10_000
ENGINE_VERSION = "weekly-multi-slot-v1"


class WeeklyMultiSlotPlanningError(ValueError):
    pass


@dataclass(frozen=True)
class WeeklyPlanningCandidate:
    evaluation: CandidateEvaluation
    plan_fit: MealPlanFitRead


@dataclass(frozen=True)
class WeeklyPlanningSlot:
    slot_key: str
    planning_date: date
    meal_type: MealType
    candidates: tuple[WeeklyPlanningCandidate, ...]


@dataclass(frozen=True)
class WeeklyPlanChoice:
    slot_key: str
    planning_date: date
    meal_type: MealType
    candidate: WeeklyPlanningCandidate


@dataclass(frozen=True)
class WeeklyPlanEvaluation:
    choices: tuple[WeeklyPlanChoice, ...]
    mandatory_minimum_occurrences_supported: int
    advisory_minimum_occurrences_supported: int
    minimum_score: Decimal
    average_score: Decimal
    repeated_candidate_count: int


@dataclass(frozen=True)
class WeeklyMultiSlotPlanningResult:
    engine_version: str
    person_id: uuid.UUID
    selected_plan: WeeklyPlanEvaluation | None
    evaluated_combinations: int
    feasible_combinations: int
    rejected_by_mandatory_weekly_maximum: int


def _week_start(value: date) -> date:
    return value - timedelta(days=value.weekday())


def _weekly_guidelines(fit: MealPlanFitRead) -> tuple[MealPlanFitGuidelineRead, ...]:
    return tuple(
        guideline
        for guideline in fit.guideline_results
        if guideline.guideline_type == "frequency" and guideline.period == "week"
    )


def _validate_candidate(
    slot: WeeklyPlanningSlot,
    candidate: WeeklyPlanningCandidate,
) -> uuid.UUID:
    evaluation = candidate.evaluation
    fit = candidate.plan_fit
    if evaluation.candidate.key != fit.candidate.key:
        raise WeeklyMultiSlotPlanningError(
            f"Slot {slot.slot_key!r} has mismatched recommendation and Plan-Fit candidates."
        )
    if fit.planning_date != slot.planning_date or fit.meal_type != slot.meal_type:
        raise WeeklyMultiSlotPlanningError(
            f"Slot {slot.slot_key!r} has Plan-Fit evidence for a different planning slot."
        )
    if evaluation.eligible and fit.eligible and evaluation.score is None:
        raise WeeklyMultiSlotPlanningError(
            f"Eligible candidate {evaluation.candidate.key!r} has no ranking score; "
            "missing score evidence is not coerced to zero."
        )
    return fit.person_id


def _normalize_slots(
    slots: tuple[WeeklyPlanningSlot, ...],
) -> tuple[tuple[WeeklyPlanningSlot, ...], uuid.UUID]:
    if not slots:
        raise WeeklyMultiSlotPlanningError("At least one planning slot is required.")
    slot_keys = [slot.slot_key for slot in slots]
    if any(not key.strip() for key in slot_keys):
        raise WeeklyMultiSlotPlanningError("Planning slot keys must be non-empty.")
    if len(set(slot_keys)) != len(slot_keys):
        raise WeeklyMultiSlotPlanningError("Planning slot keys must be unique.")

    ordered = tuple(sorted(slots, key=lambda item: (item.planning_date, item.meal_type, item.slot_key)))
    week_starts = {_week_start(slot.planning_date) for slot in ordered}
    if len(week_starts) != 1:
        raise WeeklyMultiSlotPlanningError("All planning slots must belong to the same Monday-Sunday week.")

    person_ids: set[uuid.UUID] = set()
    for slot in ordered:
        if not slot.candidates:
            raise WeeklyMultiSlotPlanningError(
                f"Planning slot {slot.slot_key!r} must contain at least one candidate."
            )
        for candidate in slot.candidates:
            person_ids.add(_validate_candidate(slot, candidate))
    if len(person_ids) != 1:
        raise WeeklyMultiSlotPlanningError(
            "The v1 multi-slot planner accepts one Person at a time; Person evidence cannot be mixed."
        )
    return ordered, next(iter(person_ids))


def _consistent_int(
    values: set[int | None],
    *,
    label: str,
    guideline_id: uuid.UUID,
) -> int | None:
    if len(values) > 1:
        raise WeeklyMultiSlotPlanningError(
            f"Inconsistent {label} for weekly guideline {guideline_id}."
        )
    return next(iter(values)) if values else None


def _consistent_bool(
    values: set[bool],
    *,
    label: str,
    guideline_id: uuid.UUID,
) -> bool:
    if len(values) > 1:
        raise WeeklyMultiSlotPlanningError(
            f"Inconsistent {label} for weekly guideline {guideline_id}."
        )
    return next(iter(values)) if values else False


def _mandatory_weekly_maximum_is_safe(choices: tuple[WeeklyPlanChoice, ...]) -> bool:
    by_guideline: dict[uuid.UUID, list[MealPlanFitGuidelineRead]] = {}
    for choice in choices:
        for guideline in _weekly_guidelines(choice.candidate.plan_fit):
            if not guideline.is_mandatory or guideline.maximum_occurrences is None:
                continue
            by_guideline.setdefault(guideline.guideline_id, []).append(guideline)

    for guideline_id, results in by_guideline.items():
        maximum = _consistent_int(
            {result.maximum_occurrences for result in results},
            label="maximum occurrence limit",
            guideline_id=guideline_id,
        )
        current = _consistent_int(
            {result.current_occurrences for result in results},
            label="current occurrence count",
            guideline_id=guideline_id,
        )
        lower_bound = _consistent_bool(
            {result.counts_are_lower_bound for result in results},
            label="lower-bound evidence status",
            guideline_id=guideline_id,
        )
        unclassified = _consistent_int(
            {result.unclassified_meal_count for result in results},
            label="unclassified meal count",
            guideline_id=guideline_id,
        )
        if maximum is None or current is None:
            return False

        known_matches = sum(result.candidate_matches is True for result in results)
        unknown_matches = sum(result.candidate_matches is None for result in results)
        possible_existing = (unclassified or 0) if lower_bound else 0
        possible_projected = current + possible_existing + known_matches + unknown_matches
        if possible_projected > maximum:
            return False
    return True


def _minimum_support(choices: tuple[WeeklyPlanChoice, ...]) -> tuple[int, int]:
    by_guideline: dict[uuid.UUID, list[MealPlanFitGuidelineRead]] = {}
    for choice in choices:
        for guideline in _weekly_guidelines(choice.candidate.plan_fit):
            if guideline.minimum_occurrences is None or guideline.status != "support":
                continue
            by_guideline.setdefault(guideline.guideline_id, []).append(guideline)

    mandatory = 0
    advisory = 0
    for guideline_id, results in by_guideline.items():
        minimum = _consistent_int(
            {result.minimum_occurrences for result in results},
            label="minimum occurrence target",
            guideline_id=guideline_id,
        )
        current = _consistent_int(
            {result.current_occurrences for result in results},
            label="current occurrence count",
            guideline_id=guideline_id,
        )
        lower_bound = _consistent_bool(
            {result.counts_are_lower_bound for result in results},
            label="lower-bound evidence status",
            guideline_id=guideline_id,
        )
        unclassified = _consistent_int(
            {result.unclassified_meal_count for result in results},
            label="unclassified meal count",
            guideline_id=guideline_id,
        )
        mandatory_flags = {result.is_mandatory for result in results}
        if len(mandatory_flags) != 1:
            raise WeeklyMultiSlotPlanningError(
                f"Inconsistent mandatory/advisory status for weekly guideline {guideline_id}."
            )
        if minimum is None or current is None:
            continue

        possible_existing = current + ((unclassified or 0) if lower_bound else 0)
        confirmed_remaining = max(0, minimum - possible_existing)
        matching_support = sum(result.candidate_matches is True for result in results)
        supported = min(confirmed_remaining, matching_support)
        if next(iter(mandatory_flags)):
            mandatory += supported
        else:
            advisory += supported
    return mandatory, advisory


def _evaluate_choices(choices: tuple[WeeklyPlanChoice, ...]) -> WeeklyPlanEvaluation:
    scores = tuple(choice.candidate.evaluation.score for choice in choices)
    if any(score is None for score in scores):
        raise WeeklyMultiSlotPlanningError(
            "A feasible weekly combination contains missing score evidence."
        )
    known_scores = tuple(score for score in scores if score is not None)
    mandatory_support, advisory_support = _minimum_support(choices)
    keys = tuple(choice.candidate.evaluation.candidate.key for choice in choices)
    return WeeklyPlanEvaluation(
        choices=choices,
        mandatory_minimum_occurrences_supported=mandatory_support,
        advisory_minimum_occurrences_supported=advisory_support,
        minimum_score=min(known_scores),
        average_score=sum(known_scores, start=Decimal(0)) / Decimal(len(known_scores)),
        repeated_candidate_count=len(keys) - len(set(keys)),
    )


def _ranking_key(plan: WeeklyPlanEvaluation) -> tuple[object, ...]:
    candidate_keys = tuple(choice.candidate.evaluation.candidate.key for choice in plan.choices)
    return (
        -plan.mandatory_minimum_occurrences_supported,
        -plan.advisory_minimum_occurrences_supported,
        -plan.minimum_score,
        -plan.average_score,
        plan.repeated_candidate_count,
        candidate_keys,
    )


def optimize_weekly_slots(
    slots: tuple[WeeklyPlanningSlot, ...],
    *,
    max_combinations: int = DEFAULT_MAX_COMBINATIONS,
) -> WeeklyMultiSlotPlanningResult:
    if max_combinations < 1:
        raise WeeklyMultiSlotPlanningError("max_combinations must be at least 1.")

    ordered_slots, person_id = _normalize_slots(slots)
    eligible_by_slot = tuple(
        tuple(
            candidate
            for candidate in slot.candidates
            if candidate.evaluation.eligible and candidate.plan_fit.eligible
        )
        for slot in ordered_slots
    )
    if any(not candidates for candidates in eligible_by_slot):
        return WeeklyMultiSlotPlanningResult(
            engine_version=ENGINE_VERSION,
            person_id=person_id,
            selected_plan=None,
            evaluated_combinations=0,
            feasible_combinations=0,
            rejected_by_mandatory_weekly_maximum=0,
        )

    combination_count = prod(len(candidates) for candidates in eligible_by_slot)
    if combination_count > max_combinations:
        raise WeeklyMultiSlotPlanningError(
            f"Weekly planning search space has {combination_count} combinations; "
            f"the deterministic v1 limit is {max_combinations}."
        )

    feasible: list[WeeklyPlanEvaluation] = []
    rejected_by_maximum = 0
    evaluated = 0
    for candidate_combination in product(*eligible_by_slot):
        evaluated += 1
        choices = tuple(
            WeeklyPlanChoice(
                slot_key=slot.slot_key,
                planning_date=slot.planning_date,
                meal_type=slot.meal_type,
                candidate=candidate,
            )
            for slot, candidate in zip(ordered_slots, candidate_combination, strict=True)
        )
        if not _mandatory_weekly_maximum_is_safe(choices):
            rejected_by_maximum += 1
            continue
        feasible.append(_evaluate_choices(choices))

    selected = min(feasible, key=_ranking_key) if feasible else None
    return WeeklyMultiSlotPlanningResult(
        engine_version=ENGINE_VERSION,
        person_id=person_id,
        selected_plan=selected,
        evaluated_combinations=evaluated,
        feasible_combinations=len(feasible),
        rejected_by_mandatory_weekly_maximum=rejected_by_maximum,
    )
