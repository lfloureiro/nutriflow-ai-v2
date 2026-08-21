import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.meal import MealEvent, MealParticipant, Serving, ServingNutritionComponent


class MealLifecycleError(ValueError):
    pass


class MealIdempotencyConflictError(MealLifecycleError):
    pass


class MealReplacementError(MealLifecycleError):
    pass


@dataclass(frozen=True)
class MealEventSpec:
    family_id: uuid.UUID
    meal_type: str
    scheduled_at: datetime
    timezone: str
    title: str | None = None
    location: str | None = None
    source: str = "user"
    source_reference: str | None = None
    notes: str | None = None
    replaces_meal_event_id: uuid.UUID | None = None


@dataclass(frozen=True)
class IdempotentMealEventResult:
    meal_event: MealEvent
    created: bool


def _is_timezone_aware(value: datetime) -> bool:
    return value.tzinfo is not None and value.utcoffset() is not None


def _validate_idempotency_key(idempotency_key: str) -> None:
    if not idempotency_key:
        raise MealLifecycleError("idempotency_key must not be empty.")
    if len(idempotency_key) > 160:
        raise MealLifecycleError("idempotency_key must not exceed 160 characters.")


def _validate_spec(spec: MealEventSpec) -> None:
    if not spec.meal_type:
        raise MealLifecycleError("meal_type must not be empty.")
    if not _is_timezone_aware(spec.scheduled_at):
        raise MealLifecycleError("scheduled_at must be timezone-aware.")
    if not spec.timezone:
        raise MealLifecycleError("timezone must not be empty.")
    if not spec.source:
        raise MealLifecycleError("source must not be empty.")


def _find_idempotent_event(
    session: Session,
    *,
    family_id: uuid.UUID,
    idempotency_key: str,
) -> MealEvent | None:
    return session.scalar(
        select(MealEvent).where(
            MealEvent.family_id == family_id,
            MealEvent.idempotency_key == idempotency_key,
        )
    )


def _event_matches_spec(event: MealEvent, spec: MealEventSpec) -> bool:
    return (
        event.family_id == spec.family_id
        and event.replaces_meal_event_id == spec.replaces_meal_event_id
        and event.meal_type == spec.meal_type
        and event.title == spec.title
        and event.scheduled_at == spec.scheduled_at
        and event.timezone == spec.timezone
        and event.location == spec.location
        and event.source == spec.source
        and event.source_reference == spec.source_reference
        and event.notes == spec.notes
    )


def create_idempotent_meal_event(
    session: Session,
    *,
    spec: MealEventSpec,
    idempotency_key: str,
) -> IdempotentMealEventResult:
    _validate_idempotency_key(idempotency_key)
    _validate_spec(spec)

    existing = _find_idempotent_event(
        session,
        family_id=spec.family_id,
        idempotency_key=idempotency_key,
    )
    if existing is not None:
        if not _event_matches_spec(existing, spec):
            raise MealIdempotencyConflictError(
                "The idempotency key is already bound to a different MealEvent request."
            )
        return IdempotentMealEventResult(meal_event=existing, created=False)

    event = MealEvent(
        family_id=spec.family_id,
        replaces_meal_event_id=spec.replaces_meal_event_id,
        meal_type=spec.meal_type,
        title=spec.title,
        scheduled_at=spec.scheduled_at,
        timezone=spec.timezone,
        status="planned",
        location=spec.location,
        source=spec.source,
        source_reference=spec.source_reference,
        idempotency_key=idempotency_key,
        notes=spec.notes,
    )
    session.add(event)
    return IdempotentMealEventResult(meal_event=event, created=True)


def _validate_replaceable(event: MealEvent) -> None:
    if event.id is None:
        raise MealReplacementError("The MealEvent must be persisted before replacement.")
    if event.status not in {"planned", "prepared"}:
        raise MealReplacementError(
            "Only planned or prepared MealEvents can be replaced before serving."
        )
    if event.served_at is not None or event.completed_at is not None:
        raise MealReplacementError("A served or completed MealEvent cannot be replaced as a plan.")

    for participant in event.participants:
        if participant.status != "planned":
            raise MealReplacementError(
                "All MealParticipants must still be planned before replacing the MealEvent."
            )
        for serving in participant.servings:
            if serving.status != "planned":
                raise MealReplacementError(
                    "All Servings must still be planned before replacing the MealEvent."
                )
            if (
                serving.quantity_served is not None
                or serving.quantity_consumed is not None
                or serving.energy_served_kcal is not None
                or serving.energy_consumed_kcal is not None
                or serving.consumed_at is not None
            ):
                raise MealReplacementError(
                    "A MealEvent with realized Serving data cannot be replaced as a plan."
                )


def _clone_serving(serving: Serving, participant: MealParticipant) -> Serving:
    cloned = Serving(
        meal_participant=participant,
        food_item=serving.food_item,
        recipe=serving.recipe,
        food_composition_snapshot=serving.food_composition_snapshot,
        recipe_composition_snapshot=serving.recipe_composition_snapshot,
        item_type=serving.item_type,
        item_key=serving.item_key,
        item_name=serving.item_name,
        status="planned",
        quantity_planned=serving.quantity_planned,
        quantity_unit=serving.quantity_unit,
        energy_planned_kcal=serving.energy_planned_kcal,
        nutrition_source=serving.nutrition_source,
        nutrition_calculation_version=serving.nutrition_calculation_version,
        source_reference=serving.source_reference,
        notes=serving.notes,
    )
    cloned.nutrition_components = [
        ServingNutritionComponent(
            nutrient_key=component.nutrient_key,
            planned_value=component.planned_value,
            unit=component.unit,
        )
        for component in serving.nutrition_components
        if component.planned_value is not None
    ]
    return cloned


def _clone_planned_content(source: MealEvent, replacement: MealEvent) -> None:
    for source_participant in source.participants:
        replacement_participant = MealParticipant(
            meal_event=replacement,
            person=source_participant.person,
            status="planned",
            notes=source_participant.notes,
        )
        replacement_participant.servings = [
            _clone_serving(serving, replacement_participant)
            for serving in source_participant.servings
        ]


def replace_meal_event_plan(
    session: Session,
    *,
    original: MealEvent,
    replacement_spec: MealEventSpec,
    idempotency_key: str,
) -> IdempotentMealEventResult:
    _validate_idempotency_key(idempotency_key)
    _validate_spec(replacement_spec)

    if original.id is None:
        raise MealReplacementError("The MealEvent must be persisted before replacement.")
    if replacement_spec.family_id != original.family_id:
        raise MealReplacementError("A replacement MealEvent must remain in the same Family.")
    if replacement_spec.replaces_meal_event_id != original.id:
        raise MealReplacementError(
            "replacement_spec.replaces_meal_event_id must reference the original MealEvent."
        )

    existing = _find_idempotent_event(
        session,
        family_id=original.family_id,
        idempotency_key=idempotency_key,
    )
    if existing is not None:
        if not _event_matches_spec(existing, replacement_spec):
            raise MealIdempotencyConflictError(
                "The idempotency key is already bound to a different replacement request."
            )
        if existing.replaces_meal_event_id != original.id:
            raise MealIdempotencyConflictError(
                "The idempotency key belongs to a replacement of another MealEvent."
            )
        return IdempotentMealEventResult(meal_event=existing, created=False)

    if original.status == "replaced":
        raise MealReplacementError(
            "The MealEvent was already replaced by a different replacement request."
        )

    _validate_replaceable(original)
    result = create_idempotent_meal_event(
        session,
        spec=replacement_spec,
        idempotency_key=idempotency_key,
    )
    _clone_planned_content(original, result.meal_event)
    original.status = "replaced"
    return result
