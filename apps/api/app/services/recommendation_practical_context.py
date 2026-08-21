from dataclasses import dataclass
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.models.daily_nutrition_state import DailyNutritionState
from app.models.food_adverse_reaction import FoodAdverseReaction
from app.models.food_preference import FoodPreference
from app.models.nutrition_constraint import NutritionConstraint
from app.models.schedule_entry import ScheduleEntry
from app.services.meal_recommendation import (
    CandidateEvaluation,
    MealCandidate,
    RecommendationResult,
    recommend_meals,
)

_WEEKDAYS = {
    "MO": 0,
    "TU": 1,
    "WE": 2,
    "TH": 3,
    "FR": 4,
    "SA": 5,
    "SU": 6,
}
_SUPPORTED_RULE_KEYS = frozenset({"FREQ", "BYDAY", "INTERVAL"})


class PracticalRecommendationError(ValueError):
    pass


class UnsupportedRecurrenceRuleError(PracticalRecommendationError):
    pass


@dataclass(frozen=True)
class CandidatePracticalProfile:
    candidate_key: str
    available_locations: frozenset[str] | None = None
    preparation_minutes: int | None = None
    requires_kitchen: bool = False


@dataclass(frozen=True)
class PracticalMealContext:
    scheduled_at: datetime
    location: str | None = None
    available_minutes: int | None = None
    has_kitchen: bool | None = None
    schedule_entries: tuple[ScheduleEntry, ...] = ()


@dataclass(frozen=True)
class ScheduleContextEvaluation:
    is_available: bool | None
    is_preferred: bool
    locations: frozenset[str]
    event_types: tuple[str, ...]


def _is_timezone_aware(value: datetime) -> bool:
    return value.tzinfo is not None and value.utcoffset() is not None


def _parse_recurrence_rule(rule: str) -> dict[str, str]:
    normalized = rule.strip()
    if normalized.upper().startswith("RRULE:"):
        normalized = normalized[6:]

    fields: dict[str, str] = {}
    for part in normalized.split(";"):
        if not part or "=" not in part:
            raise UnsupportedRecurrenceRuleError(
                f"Unsupported recurrence rule fragment: {part!r}."
            )
        key, value = part.split("=", 1)
        key = key.strip().upper()
        value = value.strip().upper()
        if not key or not value or key in fields:
            raise UnsupportedRecurrenceRuleError(
                f"Invalid recurrence rule fragment: {part!r}."
            )
        fields[key] = value

    unsupported = set(fields) - _SUPPORTED_RULE_KEYS
    if unsupported:
        raise UnsupportedRecurrenceRuleError(
            "Unsupported recurrence rule keys: " + ", ".join(sorted(unsupported)) + "."
        )

    frequency = fields.get("FREQ")
    if frequency not in {"DAILY", "WEEKLY"}:
        raise UnsupportedRecurrenceRuleError(
            "Practical planning currently supports only DAILY and WEEKLY recurrence rules."
        )

    interval_text = fields.get("INTERVAL", "1")
    try:
        interval = int(interval_text)
    except ValueError as exc:
        raise UnsupportedRecurrenceRuleError("Recurrence INTERVAL must be an integer.") from exc
    if interval != 1:
        raise UnsupportedRecurrenceRuleError(
            "Practical planning currently supports only recurrence INTERVAL=1."
        )

    if "BYDAY" in fields:
        weekdays = fields["BYDAY"].split(",")
        if not weekdays or any(weekday not in _WEEKDAYS for weekday in weekdays):
            raise UnsupportedRecurrenceRuleError(
                "Recurrence BYDAY contains an unsupported weekday value."
            )

    return fields


def _recurs_on(entry: ScheduleEntry, occurrence_date: date) -> bool:
    if entry.valid_from is None or entry.recurrence_rule is None:
        return False
    if occurrence_date < entry.valid_from:
        return False
    if entry.valid_until is not None and occurrence_date > entry.valid_until:
        return False

    fields = _parse_recurrence_rule(entry.recurrence_rule)
    frequency = fields["FREQ"]
    if "BYDAY" in fields:
        weekdays = {_WEEKDAYS[value] for value in fields["BYDAY"].split(",")}
        if occurrence_date.weekday() not in weekdays:
            return False

    if frequency == "DAILY":
        return True

    if "BYDAY" in fields:
        return True
    return occurrence_date.weekday() == entry.valid_from.weekday()


def _recurring_matches(entry: ScheduleEntry, scheduled_at: datetime) -> bool:
    if entry.local_start_time is None or entry.local_end_time is None:
        return False

    try:
        zone = ZoneInfo(entry.timezone)
    except ZoneInfoNotFoundError as exc:
        raise PracticalRecommendationError(
            f"Unknown timezone on schedule entry: {entry.timezone!r}."
        ) from exc

    local_at = scheduled_at.astimezone(zone)
    local_time = local_at.timetz().replace(tzinfo=None)
    start = entry.local_start_time
    end = entry.local_end_time

    if start == end:
        occurrence_date = local_at.date()
    elif start < end:
        if not start <= local_time < end:
            return False
        occurrence_date = local_at.date()
    else:
        if local_time >= start:
            occurrence_date = local_at.date()
        elif local_time < end:
            occurrence_date = local_at.date() - timedelta(days=1)
        else:
            return False

    return _recurs_on(entry, occurrence_date)


def _one_off_matches(entry: ScheduleEntry, scheduled_at: datetime) -> bool:
    if entry.starts_at is None or entry.ends_at is None:
        return False
    return entry.starts_at <= scheduled_at < entry.ends_at


def _matching_entries(context: PracticalMealContext) -> tuple[list[ScheduleEntry], list[ScheduleEntry]]:
    one_off: list[ScheduleEntry] = []
    recurring: list[ScheduleEntry] = []
    for entry in context.schedule_entries:
        if entry.entry_type == "one_off" and _one_off_matches(entry, context.scheduled_at):
            one_off.append(entry)
        elif entry.entry_type == "recurring" and _recurring_matches(entry, context.scheduled_at):
            recurring.append(entry)
    return one_off, recurring


def evaluate_schedule_context(context: PracticalMealContext) -> ScheduleContextEvaluation:
    if not _is_timezone_aware(context.scheduled_at):
        raise PracticalRecommendationError("scheduled_at must be timezone-aware.")
    if context.available_minutes is not None and context.available_minutes < 0:
        raise PracticalRecommendationError("available_minutes must be non-negative.")

    one_off, recurring = _matching_entries(context)
    one_off_effects = [entry for entry in one_off if entry.availability_effect != "neutral"]
    recurring_effects = [entry for entry in recurring if entry.availability_effect != "neutral"]
    effective_entries = one_off_effects if one_off_effects else recurring_effects

    is_available: bool | None = None
    if effective_entries:
        if any(entry.availability_effect == "unavailable" for entry in effective_entries):
            is_available = False
        elif any(
            entry.availability_effect in {"available", "preferred"}
            for entry in effective_entries
        ):
            is_available = True

    is_preferred = is_available is not False and any(
        entry.availability_effect == "preferred" for entry in effective_entries
    )

    location_entries = [entry for entry in one_off if entry.location]
    if not location_entries:
        location_entries = [entry for entry in recurring if entry.location]

    return ScheduleContextEvaluation(
        is_available=is_available,
        is_preferred=is_preferred,
        locations=frozenset(entry.location for entry in location_entries if entry.location),
        event_types=tuple(sorted({entry.event_type for entry in one_off + recurring})),
    )


def _profile_map(
    profiles: tuple[CandidatePracticalProfile, ...],
) -> dict[str, CandidatePracticalProfile]:
    result: dict[str, CandidatePracticalProfile] = {}
    for profile in profiles:
        if not profile.candidate_key:
            raise PracticalRecommendationError("candidate_key must not be empty.")
        if profile.candidate_key in result:
            raise PracticalRecommendationError(
                f"Duplicate practical profile for candidate {profile.candidate_key!r}."
            )
        if profile.preparation_minutes is not None and profile.preparation_minutes < 0:
            raise PracticalRecommendationError("preparation_minutes must be non-negative.")
        result[profile.candidate_key] = profile
    return result


def _resolved_location(
    context: PracticalMealContext,
    schedule: ScheduleContextEvaluation,
) -> str | None:
    if context.location:
        return context.location
    if len(schedule.locations) == 1:
        return next(iter(schedule.locations))
    return None


def _practical_exclusions(
    candidate: MealCandidate,
    profile: CandidatePracticalProfile | None,
    context: PracticalMealContext,
    schedule: ScheduleContextEvaluation,
) -> tuple[str, ...]:
    exclusions: list[str] = []
    if schedule.is_available is False:
        exclusions.append("schedule_unavailable")

    if profile is None:
        return tuple(exclusions)

    location = _resolved_location(context, schedule)
    if (
        location is not None
        and profile.available_locations is not None
        and location not in profile.available_locations
    ):
        exclusions.append(f"candidate_unavailable_at_location:{location}")

    if (
        context.available_minutes is not None
        and profile.preparation_minutes is not None
        and profile.preparation_minutes > context.available_minutes
    ):
        exclusions.append("preparation_time_exceeds_available_window")

    if profile.requires_kitchen and context.has_kitchen is False:
        exclusions.append("kitchen_required")

    return tuple(sorted(set(exclusions)))


def _practical_explanations(
    context: PracticalMealContext,
    schedule: ScheduleContextEvaluation,
) -> tuple[str, ...]:
    explanations: list[str] = []
    if schedule.is_preferred:
        explanations.append("schedule_preferred_window")
    elif schedule.is_available is True:
        explanations.append("schedule_available_window")

    location = _resolved_location(context, schedule)
    if location is not None:
        explanations.append(f"planning_location:{location}")
    return tuple(explanations)


def recommend_meals_with_practical_context(
    *,
    daily_state: DailyNutritionState,
    candidates: list[MealCandidate],
    preferences: list[FoodPreference],
    adverse_reactions: list[FoodAdverseReaction],
    constraints: list[NutritionConstraint],
    planning_date: date,
    practical_context: PracticalMealContext,
    practical_profiles: tuple[CandidatePracticalProfile, ...] = (),
    engine_version: str = "meal-recommendation-practical-v1",
) -> RecommendationResult:
    schedule = evaluate_schedule_context(practical_context)
    profiles = _profile_map(practical_profiles)

    practical_excluded: list[CandidateEvaluation] = []
    practical_candidates: list[MealCandidate] = []
    for candidate in candidates:
        exclusions = _practical_exclusions(
            candidate,
            profiles.get(candidate.key),
            practical_context,
            schedule,
        )
        if exclusions:
            practical_excluded.append(
                CandidateEvaluation(
                    candidate=candidate,
                    eligible=False,
                    rank=None,
                    score=None,
                    score_breakdown={},
                    exclusion_reasons=exclusions,
                    explanation=("Excluded by practical planning context.",),
                )
            )
        else:
            practical_candidates.append(candidate)

    base_result = recommend_meals(
        daily_state=daily_state,
        candidates=practical_candidates,
        preferences=preferences,
        adverse_reactions=adverse_reactions,
        constraints=constraints,
        planning_date=planning_date,
        engine_version=engine_version,
    )
    practical_explanations = _practical_explanations(practical_context, schedule)
    evaluated = [
        CandidateEvaluation(
            candidate=evaluation.candidate,
            eligible=evaluation.eligible,
            rank=evaluation.rank,
            score=evaluation.score,
            score_breakdown=evaluation.score_breakdown,
            exclusion_reasons=evaluation.exclusion_reasons,
            explanation=evaluation.explanation + practical_explanations,
        )
        for evaluation in base_result.evaluations
    ]
    evaluated.extend(practical_excluded)
    evaluated.sort(
        key=lambda evaluation: (
            0 if evaluation.eligible else 1,
            evaluation.rank if evaluation.rank is not None else 10**9,
            evaluation.candidate.key,
        )
    )
    return RecommendationResult(engine_version=engine_version, evaluations=tuple(evaluated))
