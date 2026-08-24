import uuid
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.family import Family
from app.models.food_catalog import FoodCompositionSnapshot, RecipeCompositionSnapshot
from app.models.meal import MealEvent, MealParticipant, Serving
from app.schemas.meal_consumption import MealConsumptionRead, MealConsumptionUpdate
from app.services.planning_bootstrap_api import get_planning_bootstrap
from app.services.serving_nutrition import (
    ServingNutritionCalculationError,
    calculate_serving_nutrition,
)

ZERO = Decimal(0)
ENERGY_QUANTUM = Decimal("0.01")
NUTRIENT_QUANTUM = Decimal("0.0001")
_REALIZED_STATUSES = frozenset({"consumed", "partial", "skipped"})
_EATEN_STATUSES = frozenset({"consumed", "partial"})


class MealConsumptionError(ValueError):
    pass


class MealConsumptionNotFoundError(MealConsumptionError):
    pass


def _load_event(
    session: Session,
    *,
    family_id: uuid.UUID,
    meal_event_id: uuid.UUID,
) -> MealEvent:
    event = session.scalar(
        select(MealEvent)
        .where(
            MealEvent.id == meal_event_id,
            MealEvent.family_id == family_id,
        )
        .options(
            selectinload(MealEvent.participants).selectinload(MealParticipant.person),
            selectinload(MealEvent.participants)
            .selectinload(MealParticipant.servings)
            .selectinload(Serving.nutrition_components),
            selectinload(MealEvent.participants)
            .selectinload(MealParticipant.servings)
            .selectinload(Serving.food_composition_snapshot)
            .selectinload(FoodCompositionSnapshot.nutrients),
            selectinload(MealEvent.participants)
            .selectinload(MealParticipant.servings)
            .selectinload(Serving.recipe_composition_snapshot)
            .selectinload(RecipeCompositionSnapshot.nutrients),
        )
    )
    if event is None:
        raise MealConsumptionNotFoundError("MealEvent not found for this Family.")
    return event


def _participant_and_serving(
    event: MealEvent,
    *,
    person_id: uuid.UUID,
    serving_id: uuid.UUID,
) -> tuple[MealParticipant, Serving]:
    participant = next(
        (item for item in event.participants if item.person_id == person_id),
        None,
    )
    if participant is None:
        raise MealConsumptionNotFoundError("Person is not a participant in this MealEvent.")
    serving = next(
        (item for item in participant.servings if item.id == serving_id),
        None,
    )
    if serving is None:
        raise MealConsumptionNotFoundError("Serving not found for this MealEvent participant.")
    return participant, serving


def _scaled(value: Decimal | None, factor: Decimal, quantum: Decimal) -> Decimal | None:
    if value is None:
        return None
    return (value * factor).quantize(quantum, rounding=ROUND_HALF_UP)


def _fallback_consumed_nutrition(serving: Serving) -> None:
    if serving.quantity_consumed is None:
        serving.energy_consumed_kcal = None
        for component in serving.nutrition_components:
            component.consumed_value = None
        return
    if serving.quantity_planned is None or serving.quantity_planned <= ZERO:
        raise MealConsumptionError(
            "Cannot estimate consumed nutrition without a planned quantity or catalogue composition."
        )
    factor = serving.quantity_consumed / serving.quantity_planned
    serving.energy_consumed_kcal = _scaled(
        serving.energy_planned_kcal,
        factor,
        ENERGY_QUANTUM,
    )
    for component in serving.nutrition_components:
        component.consumed_value = _scaled(
            component.planned_value,
            factor,
            NUTRIENT_QUANTUM,
        )


def _calculate_consumed_nutrition(serving: Serving) -> None:
    composition = serving.food_composition_snapshot or serving.recipe_composition_snapshot
    if composition is not None:
        try:
            calculate_serving_nutrition(
                serving,
                composition,
                calculation_version="serving-nutrition-consumption-v1",
            )
        except ServingNutritionCalculationError:
            # Existing planned servings can outlive catalogue/unit-model changes. Their persisted
            # planned nutrition is authoritative enough to scale consumption without returning 500.
            _fallback_consumed_nutrition(serving)
        return
    _fallback_consumed_nutrition(serving)


def _consumed_quantity(serving: Serving, data: MealConsumptionUpdate) -> Decimal:
    if data.quantity_consumed is not None:
        return data.quantity_consumed
    fallback = serving.quantity_served or serving.quantity_planned
    if fallback is None or fallback <= ZERO:
        raise MealConsumptionError(
            "A consumed Serving requires quantity_consumed or an existing served/planned quantity."
        )
    return fallback


def _apply_consumption(
    participant: MealParticipant,
    serving: Serving,
    data: MealConsumptionUpdate,
    *,
    consumed_at: datetime,
) -> None:
    if data.status == "skipped":
        participant.status = "skipped"
        serving.status = "skipped"
        serving.quantity_consumed = None
        serving.energy_consumed_kcal = None
        serving.consumed_at = None
        for component in serving.nutrition_components:
            component.consumed_value = None
        return

    quantity = _consumed_quantity(serving, data)
    participant.status = data.status
    serving.status = data.status
    serving.quantity_consumed = quantity
    served_quantity = serving.quantity_served or serving.quantity_planned
    if served_quantity is None or served_quantity < quantity:
        serving.quantity_served = quantity
    elif serving.quantity_served is None:
        serving.quantity_served = served_quantity
    serving.consumed_at = consumed_at
    _calculate_consumed_nutrition(serving)


def _refresh_event_status(event: MealEvent, *, now: datetime) -> None:
    statuses = [participant.status for participant in event.participants]
    any_eaten = any(status in _EATEN_STATUSES for status in statuses)
    if statuses and all(status in _REALIZED_STATUSES for status in statuses):
        event.status = "completed"
        event.served_at = (event.served_at or now) if any_eaten else None
        event.completed_at = now
        return
    if any_eaten:
        event.status = "served"
        event.served_at = event.served_at or now
        event.completed_at = None
        return
    event.status = "planned"
    event.served_at = None
    event.completed_at = None


def record_meal_consumption(
    session: Session,
    *,
    family: Family,
    meal_event_id: uuid.UUID,
    person_id: uuid.UUID,
    serving_id: uuid.UUID,
    data: MealConsumptionUpdate,
    now: datetime | None = None,
) -> MealConsumptionRead:
    event = _load_event(
        session,
        family_id=family.id,
        meal_event_id=meal_event_id,
    )
    if event.status in {"cancelled", "replaced"}:
        raise MealConsumptionError("Cancelled or replaced MealEvents cannot record consumption.")

    participant, serving = _participant_and_serving(
        event,
        person_id=person_id,
        serving_id=serving_id,
    )
    instant = now or datetime.now(UTC)
    _apply_consumption(
        participant,
        serving,
        data,
        consumed_at=instant,
    )
    _refresh_event_status(event, now=instant)
    session.flush()

    bootstrap = get_planning_bootstrap(
        session,
        person_id=person_id,
        scheduled_at=event.scheduled_at,
        ensure_state=True,
        force_state_refresh=True,
    )
    state = bootstrap.daily_nutrition_state
    if state is None:
        raise MealConsumptionError("Daily nutrition state could not be refreshed.")

    return MealConsumptionRead(
        meal_event_id=event.id,
        person_id=person_id,
        serving_id=serving.id,
        status=data.status,
        quantity_planned=serving.quantity_planned,
        quantity_consumed=serving.quantity_consumed,
        quantity_unit=serving.quantity_unit,
        energy_planned_kcal=serving.energy_planned_kcal,
        energy_consumed_kcal=serving.energy_consumed_kcal,
        consumed_at=serving.consumed_at,
        daily_nutrition_state=state,
    )
