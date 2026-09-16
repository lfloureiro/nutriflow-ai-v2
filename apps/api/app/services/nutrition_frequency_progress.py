import uuid
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.food_catalog import FoodItem, Recipe
from app.models.meal import MealEvent, MealParticipant, Serving
from app.models.nutrition_plan import NutritionPlan, NutritionPlanGuideline
from app.models.person import Person
from app.schemas.meal_type import MEAL_TYPES
from app.schemas.nutrition_frequency_progress import (
    FrequencyProgressStatus,
    WeeklyFrequencyGuidelineProgressRead,
    WeeklyNutritionFrequencyProgressRead,
)
from app.schemas.nutrition_plan import EffectiveNutritionGuidelineRead
from app.services.nutrition_plan import NutritionPlanError, compile_effective_nutrition_plan

_COMPLETED_PARTICIPANT_STATUSES = frozenset({"consumed", "partial"})
_PLANNED_PARTICIPANT_STATUSES = frozenset({"planned", "served"})
_COMPLETED_SERVING_STATUSES = frozenset({"consumed", "partial"})
_PLANNED_SERVING_STATUSES = frozenset({"planned", "served"})
_EXCLUDED_EVENT_STATUSES = frozenset({"cancelled", "replaced"})
_EXCLUDED_PARTICIPANT_STATUSES = frozenset({"skipped", "replaced"})
_EXCLUDED_SERVING_STATUSES = frozenset({"skipped", "replaced"})
_SUPPORTED_TARGET_TYPES = frozenset({"meal_type", "food_item", "recipe"})


class NutritionFrequencyProgressError(ValueError):
    pass


def _week_bounds(on_date: date) -> tuple[date, date]:
    start = on_date - timedelta(days=on_date.weekday())
    return start, start + timedelta(days=6)


def _effective_frequency_guidelines(
    db: Session,
    *,
    person_id: uuid.UUID,
    on_date: date,
) -> list[EffectiveNutritionGuidelineRead]:
    by_id: dict[uuid.UUID, EffectiveNutritionGuidelineRead] = {}
    for meal_type in MEAL_TYPES:
        try:
            effective = compile_effective_nutrition_plan(
                db,
                person_id=person_id,
                on_date=on_date,
                meal_type=meal_type,
            )
        except NutritionPlanError as exc:
            raise NutritionFrequencyProgressError(str(exc)) from exc
        for guideline in effective.guidelines:
            if guideline.guideline_type == "frequency" and guideline.period == "week":
                by_id[guideline.id] = guideline
    return sorted(by_id.values(), key=lambda item: (-item.priority, str(item.id)))


def _load_participations(
    db: Session,
    *,
    person_id: uuid.UUID,
    timezone: ZoneInfo,
    week_start: date,
    week_end: date,
) -> list[MealParticipant]:
    start_at = datetime.combine(week_start, time.min, tzinfo=timezone)
    end_at = datetime.combine(week_end + timedelta(days=1), time.min, tzinfo=timezone)
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


def _guideline_date_window(
    db: Session,
    *,
    guideline: EffectiveNutritionGuidelineRead,
    week_start: date,
    week_end: date,
) -> tuple[date, date]:
    start = week_start
    end = week_end
    persisted = db.get(NutritionPlanGuideline, guideline.id)
    if persisted is not None:
        if persisted.valid_from is not None:
            start = max(start, persisted.valid_from)
        if persisted.valid_until is not None:
            end = min(end, persisted.valid_until)

    plan_id = guideline.source.plan_id
    if plan_id is not None:
        plan = db.get(NutritionPlan, plan_id)
        if plan is not None:
            start = max(start, plan.valid_from)
            if plan.valid_until is not None:
                end = min(end, plan.valid_until)
    return start, end


def _serving_matches(serving: Serving, *, target_type: str, target_key: str) -> bool:
    if serving.status in _EXCLUDED_SERVING_STATUSES:
        return False
    if target_type == "food_item":
        if serving.item_key == target_key:
            return True
        food_item: FoodItem | None = serving.food_item
        return food_item is not None and food_item.catalog_key == target_key
    if target_type == "recipe":
        if serving.item_key == target_key:
            return True
        recipe: Recipe | None = serving.recipe
        return recipe is not None and recipe.recipe_key == target_key
    return False


def _matching_status(
    participant: MealParticipant,
    *,
    guideline: EffectiveNutritionGuidelineRead,
    timezone: ZoneInfo,
    valid_start: date,
    valid_end: date,
) -> str | None:
    event = participant.meal_event
    local_date = event.scheduled_at.astimezone(timezone).date()
    if local_date < valid_start or local_date > valid_end:
        return None
    if guideline.meal_type is not None and event.meal_type != guideline.meal_type:
        return None

    target_type = guideline.target_type
    target_key = guideline.target_key
    if target_type == "meal_type":
        if event.meal_type != target_key:
            return None
        if participant.status in _COMPLETED_PARTICIPANT_STATUSES:
            return "completed"
        if participant.status in _PLANNED_PARTICIPANT_STATUSES:
            return "planned"
        return None

    if target_type not in {"food_item", "recipe"} or target_key is None:
        return None

    matching = [
        serving
        for serving in participant.servings
        if _serving_matches(serving, target_type=target_type, target_key=target_key)
    ]
    if any(serving.status in _COMPLETED_SERVING_STATUSES for serving in matching):
        return "completed"
    if any(serving.status in _PLANNED_SERVING_STATUSES for serving in matching):
        return "planned"
    return None


def _status_for_count(
    count: int,
    *,
    minimum: int | None,
    maximum: int | None,
) -> FrequencyProgressStatus:
    if maximum is not None and count > maximum:
        return "above_maximum"
    if minimum is not None and count < minimum:
        return "below_minimum"
    return "within_bounds"


def _unknown_progress(
    guideline: EffectiveNutritionGuidelineRead,
    *,
    reason: str,
) -> WeeklyFrequencyGuidelineProgressRead:
    return WeeklyFrequencyGuidelineProgressRead(
        guideline_id=guideline.id,
        description=guideline.description,
        target_type=guideline.target_type,
        target_key=guideline.target_key,
        meal_type=guideline.meal_type,
        minimum_occurrences=guideline.minimum_occurrences,
        maximum_occurrences=guideline.maximum_occurrences,
        is_mandatory=guideline.is_mandatory,
        severity=guideline.severity,
        evidence_status="unknown",
        current_status="unknown",
        projected_status="unknown",
        completed_occurrences=None,
        planned_occurrences=None,
        projected_occurrences=None,
        remaining_minimum=None,
        remaining_capacity=None,
        unknown_reason=reason,
    )


def get_weekly_nutrition_frequency_progress(
    db: Session,
    *,
    person_id: uuid.UUID,
    on_date: date,
) -> WeeklyNutritionFrequencyProgressRead:
    person = db.get(Person, person_id)
    if person is None:
        raise NutritionFrequencyProgressError("Person not found.")
    try:
        timezone = ZoneInfo(person.timezone)
    except ZoneInfoNotFoundError as exc:
        raise NutritionFrequencyProgressError(
            f"Person has an unknown timezone: {person.timezone!r}."
        ) from exc

    week_start, week_end = _week_bounds(on_date)
    guidelines = _effective_frequency_guidelines(
        db,
        person_id=person_id,
        on_date=on_date,
    )
    participations = _load_participations(
        db,
        person_id=person_id,
        timezone=timezone,
        week_start=week_start,
        week_end=week_end,
    )

    progress: list[WeeklyFrequencyGuidelineProgressRead] = []
    for guideline in guidelines:
        if guideline.target_type == "food_category":
            progress.append(
                _unknown_progress(
                    guideline,
                    reason="structured_food_category_evidence_unavailable",
                )
            )
            continue
        if (
            guideline.target_type not in _SUPPORTED_TARGET_TYPES
            or guideline.target_key is None
        ):
            progress.append(
                _unknown_progress(guideline, reason="unsupported_frequency_target")
            )
            continue
        if guideline.target_type == "meal_type" and guideline.target_key not in MEAL_TYPES:
            progress.append(
                _unknown_progress(guideline, reason="unsupported_meal_type_target")
            )
            continue

        valid_start, valid_end = _guideline_date_window(
            db,
            guideline=guideline,
            week_start=week_start,
            week_end=week_end,
        )
        completed_event_ids: set[uuid.UUID] = set()
        planned_event_ids: set[uuid.UUID] = set()
        if valid_start <= valid_end:
            for participant in participations:
                match_status = _matching_status(
                    participant,
                    guideline=guideline,
                    timezone=timezone,
                    valid_start=valid_start,
                    valid_end=valid_end,
                )
                if match_status == "completed":
                    completed_event_ids.add(participant.meal_event_id)
                elif match_status == "planned":
                    planned_event_ids.add(participant.meal_event_id)

        planned_event_ids -= completed_event_ids
        completed = len(completed_event_ids)
        planned = len(planned_event_ids)
        projected = completed + planned
        minimum = guideline.minimum_occurrences
        maximum = guideline.maximum_occurrences
        progress.append(
            WeeklyFrequencyGuidelineProgressRead(
                guideline_id=guideline.id,
                description=guideline.description,
                target_type=guideline.target_type,
                target_key=guideline.target_key,
                meal_type=guideline.meal_type,
                minimum_occurrences=minimum,
                maximum_occurrences=maximum,
                is_mandatory=guideline.is_mandatory,
                severity=guideline.severity,
                evidence_status="available",
                current_status=_status_for_count(
                    completed,
                    minimum=minimum,
                    maximum=maximum,
                ),
                projected_status=_status_for_count(
                    projected,
                    minimum=minimum,
                    maximum=maximum,
                ),
                completed_occurrences=completed,
                planned_occurrences=planned,
                projected_occurrences=projected,
                remaining_minimum=(
                    None if minimum is None else max(minimum - projected, 0)
                ),
                remaining_capacity=(
                    None if maximum is None else max(maximum - projected, 0)
                ),
                unknown_reason=None,
            )
        )

    return WeeklyNutritionFrequencyProgressRead(
        person_id=person.id,
        as_of_date=on_date,
        week_start=week_start,
        week_end=week_end,
        timezone=person.timezone,
        guidelines=progress,
    )
