import uuid
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.meal import MealEvent, MealParticipant, Serving
from app.models.meal_candidate_planning_profile import MealCandidatePlanningProfile
from app.models.person import Person
from app.schemas.meal_type import MealType
from app.schemas.nutrition_plan import EffectiveNutritionGuidelineRead
from app.schemas.weekly_frequency_progress import (
    WeeklyFrequencyGuidelineProgressRead,
    WeeklyFrequencyOccurrenceRead,
    WeeklyFrequencyProgressRead,
)
from app.services.nutrition_plan import NutritionPlanError, compile_effective_nutrition_plan

_MEAL_TYPES: tuple[MealType, ...] = ("breakfast", "lunch", "snack", "dinner")
_EXCLUDED_EVENT_STATUSES = frozenset({"cancelled", "replaced"})
_EXCLUDED_PARTICIPANT_STATUSES = frozenset({"skipped", "replaced"})
_EXCLUDED_SERVING_STATUSES = frozenset({"skipped", "replaced"})
_COMPLETED_PARTICIPANT_STATUSES = frozenset({"consumed", "partial"})
_COMPLETED_SERVING_STATUSES = frozenset({"consumed", "partial"})
_SUPPORTED_TARGET_TYPES = frozenset(
    {
        "food_category",
        "food_group",
        "planning_category",
        "primary_protein",
        "food_item",
        "recipe",
    }
)


class WeeklyFrequencyProgressError(ValueError):
    pass


def _person_zone(person: Person) -> ZoneInfo:
    try:
        return ZoneInfo(person.timezone)
    except ZoneInfoNotFoundError as exc:
        raise WeeklyFrequencyProgressError(
            f"Person has an unknown timezone: {person.timezone!r}."
        ) from exc


def _week_bounds(anchor_date: date, zone: ZoneInfo) -> tuple[date, date, datetime, datetime]:
    week_start = anchor_date - timedelta(days=anchor_date.weekday())
    week_end = week_start + timedelta(days=6)
    start_at = datetime.combine(week_start, time.min, tzinfo=zone)
    end_at = datetime.combine(week_start + timedelta(days=7), time.min, tzinfo=zone)
    return week_start, week_end, start_at, end_at


def _frequency_guidelines(
    db: Session,
    *,
    person_id: uuid.UUID,
    anchor_date: date,
) -> list[EffectiveNutritionGuidelineRead]:
    by_id: dict[uuid.UUID, EffectiveNutritionGuidelineRead] = {}
    try:
        for meal_type in _MEAL_TYPES:
            effective = compile_effective_nutrition_plan(
                db,
                person_id=person_id,
                on_date=anchor_date,
                meal_type=meal_type,
            )
            for guideline in effective.guidelines:
                if guideline.guideline_type == "frequency" and guideline.period == "week":
                    by_id[guideline.id] = guideline
    except NutritionPlanError as exc:
        raise WeeklyFrequencyProgressError(str(exc)) from exc
    return sorted(
        by_id.values(),
        key=lambda guideline: (-guideline.priority, str(guideline.id)),
    )


def _participants_in_week(
    db: Session,
    *,
    person_id: uuid.UUID,
    start_at: datetime,
    end_at: datetime,
) -> list[MealParticipant]:
    return list(
        db.scalars(
            select(MealParticipant)
            .join(MealEvent, MealEvent.id == MealParticipant.meal_event_id)
            .where(
                MealParticipant.person_id == person_id,
                MealEvent.scheduled_at >= start_at,
                MealEvent.scheduled_at < end_at,
                ~MealEvent.status.in_(_EXCLUDED_EVENT_STATUSES),
                ~MealParticipant.status.in_(_EXCLUDED_PARTICIPANT_STATUSES),
            )
            .options(
                selectinload(MealParticipant.meal_event),
                selectinload(MealParticipant.servings).selectinload(Serving.food_item),
                selectinload(MealParticipant.servings).selectinload(Serving.recipe),
            )
            .order_by(MealEvent.scheduled_at, MealParticipant.id)
        ).all()
    )


def _profile_maps(
    db: Session,
    *,
    family_id: uuid.UUID,
) -> tuple[
    dict[uuid.UUID, MealCandidatePlanningProfile],
    dict[uuid.UUID, MealCandidatePlanningProfile],
]:
    rows = db.scalars(
        select(MealCandidatePlanningProfile).where(
            MealCandidatePlanningProfile.family_id == family_id
        )
    ).all()
    food_profiles = {
        profile.food_item_id: profile
        for profile in rows
        if profile.food_item_id is not None
    }
    recipe_profiles = {
        profile.recipe_id: profile
        for profile in rows
        if profile.recipe_id is not None
    }
    return food_profiles, recipe_profiles


def _normalize(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().casefold()
    return normalized or None


def _serving_profile(
    serving: Serving,
    *,
    food_profiles: dict[uuid.UUID, MealCandidatePlanningProfile],
    recipe_profiles: dict[uuid.UUID, MealCandidatePlanningProfile],
) -> MealCandidatePlanningProfile | None:
    if serving.food_item_id is not None:
        return food_profiles.get(serving.food_item_id)
    if serving.recipe_id is not None:
        return recipe_profiles.get(serving.recipe_id)
    return None


def _serving_match(
    serving: Serving,
    guideline: EffectiveNutritionGuidelineRead,
    *,
    food_profiles: dict[uuid.UUID, MealCandidatePlanningProfile],
    recipe_profiles: dict[uuid.UUID, MealCandidatePlanningProfile],
) -> tuple[bool | None, str | None]:
    target_type = _normalize(guideline.target_type)
    target_key = _normalize(guideline.target_key)
    if target_type is None or target_key is None or target_type not in _SUPPORTED_TARGET_TYPES:
        return None, None

    if target_type == "food_item":
        if serving.food_item is not None:
            return _normalize(serving.food_item.catalog_key) == target_key, "food_item"
        if serving.recipe_id is not None:
            return False, None
        return None, None

    if target_type == "recipe":
        if serving.recipe is not None:
            return _normalize(serving.recipe.recipe_key) == target_key, "recipe"
        if serving.food_item_id is not None:
            return False, None
        return None, None

    profile = _serving_profile(
        serving,
        food_profiles=food_profiles,
        recipe_profiles=recipe_profiles,
    )
    if profile is None:
        return None, None

    planning_category = _normalize(profile.planning_category)
    primary_protein = _normalize(profile.primary_protein)
    if target_type == "planning_category":
        if planning_category is None:
            return None, None
        return planning_category == target_key, "planning_category"
    if target_type == "primary_protein":
        if primary_protein is None:
            return None, None
        return primary_protein == target_key, "primary_protein"

    # Imported plans use food_category. food_group remains a compatibility alias.
    # Both resolve only from explicit persisted planning metadata; food names and
    # descriptions are never interpreted here.
    values = {
        key: value
        for key, value in (
            ("planning_category", planning_category),
            ("primary_protein", primary_protein),
        )
        if value is not None
    }
    if not values:
        return None, None
    matched_by = [key for key, value in values.items() if value == target_key]
    if matched_by:
        return True, "+".join(sorted(matched_by))
    return False, None


def _occurrence_status(participant: MealParticipant, matching_servings: list[Serving]) -> str:
    if participant.status in _COMPLETED_PARTICIPANT_STATUSES:
        return "completed"
    if participant.meal_event.status == "completed":
        return "completed"
    if any(serving.status in _COMPLETED_SERVING_STATUSES for serving in matching_servings):
        return "completed"
    return "planned"


def _progress_state(
    *,
    minimum: int | None,
    maximum: int | None,
    total: int,
) -> str:
    if maximum is not None and total > maximum:
        return "exceeded"
    if minimum is not None and total >= minimum:
        return "achieved"
    return "in_progress"


def _unsupported_progress(
    guideline: EffectiveNutritionGuidelineRead,
) -> WeeklyFrequencyGuidelineProgressRead:
    return WeeklyFrequencyGuidelineProgressRead(
        guideline_id=guideline.id,
        description=guideline.description,
        target_type=guideline.target_type,
        target_key=guideline.target_key,
        meal_type=guideline.meal_type,
        minimum_occurrences=guideline.minimum_occurrences,
        maximum_occurrences=guideline.maximum_occurrences,
        severity=guideline.severity,
        is_mandatory=guideline.is_mandatory,
        priority=guideline.priority,
        completed_occurrences=None,
        planned_occurrences=None,
        total_occurrences=None,
        remaining_minimum=None,
        remaining_capacity=None,
        unclassified_meal_count=None,
        counts_are_lower_bound=False,
        state="unknown",
        evidence_status="unsupported_target",
        occurrences=[],
        source=guideline.source,
    )


def _guideline_progress(
    guideline: EffectiveNutritionGuidelineRead,
    *,
    participants: list[MealParticipant],
    food_profiles: dict[uuid.UUID, MealCandidatePlanningProfile],
    recipe_profiles: dict[uuid.UUID, MealCandidatePlanningProfile],
) -> WeeklyFrequencyGuidelineProgressRead:
    target_type = _normalize(guideline.target_type)
    target_key = _normalize(guideline.target_key)
    if target_type not in _SUPPORTED_TARGET_TYPES or target_key is None:
        return _unsupported_progress(guideline)

    occurrences: list[WeeklyFrequencyOccurrenceRead] = []
    unclassified_meal_count = 0
    for participant in participants:
        event = participant.meal_event
        if guideline.meal_type is not None and event.meal_type != guideline.meal_type:
            continue
        if event.meal_type not in _MEAL_TYPES:
            continue

        matching_servings: list[Serving] = []
        matched_by: set[str] = set()
        has_unknown = False
        considered_serving = False
        for serving in participant.servings:
            if serving.status in _EXCLUDED_SERVING_STATUSES:
                continue
            considered_serving = True
            matches, reason = _serving_match(
                serving,
                guideline,
                food_profiles=food_profiles,
                recipe_profiles=recipe_profiles,
            )
            if matches is True:
                matching_servings.append(serving)
                if reason is not None:
                    matched_by.update(reason.split("+"))
            elif matches is None:
                has_unknown = True

        if matching_servings:
            occurrences.append(
                WeeklyFrequencyOccurrenceRead(
                    meal_event_id=event.id,
                    scheduled_at=event.scheduled_at,
                    meal_type=event.meal_type,
                    status=_occurrence_status(participant, matching_servings),
                    matched_by=sorted(matched_by),
                )
            )
        elif has_unknown or not considered_serving:
            unclassified_meal_count += 1

    completed = sum(1 for occurrence in occurrences if occurrence.status == "completed")
    planned = sum(1 for occurrence in occurrences if occurrence.status == "planned")
    total = completed + planned
    minimum = guideline.minimum_occurrences
    maximum = guideline.maximum_occurrences
    remaining_minimum = None if minimum is None else max(minimum - total, 0)
    remaining_capacity = None if maximum is None else max(maximum - total, 0)

    return WeeklyFrequencyGuidelineProgressRead(
        guideline_id=guideline.id,
        description=guideline.description,
        target_type=guideline.target_type,
        target_key=guideline.target_key,
        meal_type=guideline.meal_type,
        minimum_occurrences=minimum,
        maximum_occurrences=maximum,
        severity=guideline.severity,
        is_mandatory=guideline.is_mandatory,
        priority=guideline.priority,
        completed_occurrences=completed,
        planned_occurrences=planned,
        total_occurrences=total,
        remaining_minimum=remaining_minimum,
        remaining_capacity=remaining_capacity,
        unclassified_meal_count=unclassified_meal_count,
        counts_are_lower_bound=unclassified_meal_count > 0,
        state=_progress_state(
            minimum=minimum,
            maximum=maximum,
            total=total,
        ),
        evidence_status="evaluated",
        occurrences=occurrences,
        source=guideline.source,
    )


def get_weekly_frequency_progress(
    db: Session,
    *,
    person_id: uuid.UUID,
    anchor_date: date,
) -> WeeklyFrequencyProgressRead:
    person = db.get(Person, person_id)
    if person is None:
        raise WeeklyFrequencyProgressError("Person not found.")
    zone = _person_zone(person)
    week_start, week_end, start_at, end_at = _week_bounds(anchor_date, zone)
    guidelines = _frequency_guidelines(
        db,
        person_id=person_id,
        anchor_date=anchor_date,
    )
    participants = _participants_in_week(
        db,
        person_id=person_id,
        start_at=start_at,
        end_at=end_at,
    )
    food_profiles, recipe_profiles = _profile_maps(
        db,
        family_id=person.family_id,
    )

    return WeeklyFrequencyProgressRead(
        person_id=person.id,
        timezone=person.timezone,
        anchor_date=anchor_date,
        week_start=week_start,
        week_end=week_end,
        guidelines=[
            _guideline_progress(
                guideline,
                participants=participants,
                food_profiles=food_profiles,
                recipe_profiles=recipe_profiles,
            )
            for guideline in guidelines
        ],
    )
