import uuid
from datetime import UTC, date, datetime, time, timedelta
from decimal import ROUND_HALF_UP, Decimal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.daily_nutrition_state import DailyNutritionState, DailyNutritionStateComponent
from app.models.meal import MealEvent, MealParticipant, Serving, ServingNutritionComponent
from app.models.nutrition_target import NutritionTarget, NutritionTargetComponent
from app.models.person import Person
from app.services.serving_nutrition import UnsupportedUnitConversionError, convert_quantity

ZERO = Decimal(0)
ENERGY_QUANTUM = Decimal("0.01")
NUTRIENT_QUANTUM = Decimal("0.0001")
_REALIZED_STATUSES = frozenset({"consumed", "partial"})
_EXCLUDED_EVENT_STATUSES = ("cancelled", "replaced")
_EXCLUDED_PARTICIPANT_STATUSES = ("skipped", "replaced")
_EXCLUDED_SERVING_STATUSES = ("skipped", "replaced")


class DailyNutritionStateRecalculationError(ValueError):
    pass


def _quantize(value: Decimal, quantum: Decimal) -> Decimal:
    return value.quantize(quantum, rounding=ROUND_HALF_UP)


def _day_window(state_date: date, timezone: str) -> tuple[datetime, datetime]:
    try:
        zone = ZoneInfo(timezone)
    except ZoneInfoNotFoundError as exc:
        raise DailyNutritionStateRecalculationError(
            f"Unknown timezone for DailyNutritionState recalculation: {timezone!r}."
        ) from exc

    start = datetime.combine(state_date, time.min, tzinfo=zone)
    end = datetime.combine(state_date + timedelta(days=1), time.min, tzinfo=zone)
    return start, end


def _validate_target(
    person: Person,
    state_date: date,
    target: NutritionTarget | None,
) -> None:
    if target is None:
        return
    if person.id is None or target.id is None:
        raise DailyNutritionStateRecalculationError(
            "Person and NutritionTarget must be persisted before recalculation."
        )
    if target.person_id != person.id:
        raise DailyNutritionStateRecalculationError(
            "NutritionTarget belongs to a different Person than the daily state."
        )
    if state_date < target.valid_from or (
        target.valid_until is not None and state_date > target.valid_until
    ):
        raise DailyNutritionStateRecalculationError(
            "NutritionTarget is not valid on the requested daily-state date."
        )


def _load_servings(
    session: Session,
    *,
    person: Person,
    window_start: datetime,
    window_end: datetime,
) -> list[Serving]:
    if person.id is None:
        raise DailyNutritionStateRecalculationError(
            "Person must be persisted before DailyNutritionState recalculation."
        )

    statement = (
        select(Serving)
        .join(Serving.meal_participant)
        .join(MealParticipant.meal_event)
        .where(
            MealParticipant.person_id == person.id,
            MealEvent.scheduled_at >= window_start,
            MealEvent.scheduled_at < window_end,
            ~MealEvent.status.in_(_EXCLUDED_EVENT_STATUSES),
            ~MealParticipant.status.in_(_EXCLUDED_PARTICIPANT_STATUSES),
            ~Serving.status.in_(_EXCLUDED_SERVING_STATUSES),
        )
        .options(selectinload(Serving.nutrition_components))
        .order_by(MealEvent.scheduled_at, Serving.created_at, Serving.id)
    )
    return list(session.scalars(statement).all())


def _is_realized(serving: Serving) -> bool:
    if serving.status in _REALIZED_STATUSES or serving.energy_consumed_kcal is not None:
        return True
    return any(component.consumed_value is not None for component in serving.nutrition_components)


def _planned_energy(serving: Serving) -> Decimal:
    if _is_realized(serving):
        return ZERO
    if serving.status == "served" and serving.energy_served_kcal is not None:
        return serving.energy_served_kcal
    return serving.energy_planned_kcal or ZERO


def _consumed_energy(serving: Serving) -> Decimal:
    return serving.energy_consumed_kcal or ZERO


def _planned_nutrient(
    serving: Serving,
    component: ServingNutritionComponent,
) -> Decimal:
    if _is_realized(serving):
        return ZERO
    if serving.status == "served" and component.served_value is not None:
        return component.served_value
    return component.planned_value or ZERO


def _consumed_nutrient(component: ServingNutritionComponent) -> Decimal:
    return component.consumed_value or ZERO


def _convert_nutrient(
    value: Decimal,
    *,
    from_unit: str,
    target: NutritionTargetComponent,
) -> Decimal:
    try:
        return convert_quantity(value, from_unit, target.unit)
    except UnsupportedUnitConversionError as exc:
        raise DailyNutritionStateRecalculationError(
            "Cannot safely aggregate nutrient "
            f"{target.target_key!r} from {from_unit!r} into target unit {target.unit!r}."
        ) from exc


def _remaining_bounds(
    target: NutritionTargetComponent,
    total: Decimal,
) -> tuple[Decimal | None, Decimal | None]:
    if target.value_min is None and target.value_max is None and target.value_target is not None:
        remaining = _quantize(target.value_target - total, NUTRIENT_QUANTUM)
        return remaining, remaining

    remaining_min = (
        _quantize(target.value_min - total, NUTRIENT_QUANTUM)
        if target.value_min is not None
        else None
    )
    remaining_max = (
        _quantize(target.value_max - total, NUTRIENT_QUANTUM)
        if target.value_max is not None
        else None
    )
    return remaining_min, remaining_max


def _build_components(
    servings: list[Serving],
    target: NutritionTarget | None,
) -> list[DailyNutritionStateComponent]:
    if target is None:
        return []

    target_components = [
        component for component in target.components if component.target_type == "nutrient"
    ]
    result: list[DailyNutritionStateComponent] = []

    for target_component in target_components:
        consumed = ZERO
        planned = ZERO
        for serving in servings:
            serving_component = next(
                (
                    component
                    for component in serving.nutrition_components
                    if component.nutrient_key == target_component.target_key
                ),
                None,
            )
            if serving_component is None:
                continue

            consumed += _convert_nutrient(
                _consumed_nutrient(serving_component),
                from_unit=serving_component.unit,
                target=target_component,
            )
            planned += _convert_nutrient(
                _planned_nutrient(serving, serving_component),
                from_unit=serving_component.unit,
                target=target_component,
            )

        consumed = _quantize(consumed, NUTRIENT_QUANTUM)
        planned = _quantize(planned, NUTRIENT_QUANTUM)
        remaining_min, remaining_max = _remaining_bounds(
            target_component,
            consumed + planned,
        )
        result.append(
            DailyNutritionStateComponent(
                target_type="nutrient",
                target_key=target_component.target_key,
                consumed_value=consumed,
                planned_value=planned,
                remaining_min=remaining_min,
                remaining_max=remaining_max,
                unit=target_component.unit,
            )
        )

    return result


def _apply_components(
    state: DailyNutritionState,
    calculated: list[DailyNutritionStateComponent],
) -> None:
    existing = {
        (component.target_type, component.target_key): component for component in state.components
    }
    desired_keys: set[tuple[str, str]] = set()

    for calculated_component in calculated:
        key = (calculated_component.target_type, calculated_component.target_key)
        desired_keys.add(key)
        current = existing.get(key)
        if current is None:
            state.components.append(calculated_component)
            continue

        current.consumed_value = calculated_component.consumed_value
        current.planned_value = calculated_component.planned_value
        current.remaining_min = calculated_component.remaining_min
        current.remaining_max = calculated_component.remaining_max
        current.unit = calculated_component.unit

    for current in list(state.components):
        key = (current.target_type, current.target_key)
        if key not in desired_keys:
            state.components.remove(current)


def _existing_state(
    session: Session,
    *,
    person_id: uuid.UUID,
    state_date: date,
    calculation_version: str,
) -> DailyNutritionState | None:
    statement = (
        select(DailyNutritionState)
        .where(
            DailyNutritionState.person_id == person_id,
            DailyNutritionState.state_date == state_date,
            DailyNutritionState.calculation_version == calculation_version,
        )
        .options(selectinload(DailyNutritionState.components))
    )
    return session.scalar(statement)


def recalculate_daily_nutrition_state(
    session: Session,
    *,
    person: Person,
    state_date: date,
    timezone: str,
    nutrition_target: NutritionTarget | None = None,
    assumed_energy_kcal: Decimal = ZERO,
    assumption_inputs: dict[str, object] | None = None,
    calculation_version: str = "daily-nutrition-from-servings-v1",
) -> DailyNutritionState:
    if not calculation_version:
        raise DailyNutritionStateRecalculationError("calculation_version must not be empty.")
    if person.id is None:
        raise DailyNutritionStateRecalculationError(
            "Person must be persisted before DailyNutritionState recalculation."
        )
    if assumed_energy_kcal < ZERO:
        raise DailyNutritionStateRecalculationError("assumed_energy_kcal cannot be negative.")

    _validate_target(person, state_date, nutrition_target)
    window_start, window_end = _day_window(state_date, timezone)
    servings = _load_servings(
        session,
        person=person,
        window_start=window_start,
        window_end=window_end,
    )

    consumed_energy = _quantize(
        sum((_consumed_energy(serving) for serving in servings), start=ZERO),
        ENERGY_QUANTUM,
    )
    planned_energy = _quantize(
        sum((_planned_energy(serving) for serving in servings), start=ZERO),
        ENERGY_QUANTUM,
    )
    assumed_energy = _quantize(assumed_energy_kcal, ENERGY_QUANTUM)
    total_energy = consumed_energy + planned_energy + assumed_energy

    remaining_energy_min = (
        _quantize(nutrition_target.energy_min_kcal - total_energy, ENERGY_QUANTUM)
        if nutrition_target is not None and nutrition_target.energy_min_kcal is not None
        else None
    )
    remaining_energy_max = (
        _quantize(nutrition_target.energy_max_kcal - total_energy, ENERGY_QUANTUM)
        if nutrition_target is not None and nutrition_target.energy_max_kcal is not None
        else None
    )

    state = _existing_state(
        session,
        person_id=person.id,
        state_date=state_date,
        calculation_version=calculation_version,
    )
    if state is None:
        state = DailyNutritionState(
            person=person,
            state_date=state_date,
            timezone=timezone,
            calculation_version=calculation_version,
        )
        session.add(state)

    state.nutrition_target = nutrition_target
    state.timezone = timezone
    state.energy_consumed_kcal = consumed_energy
    state.energy_planned_kcal = planned_energy
    state.energy_assumed_kcal = assumed_energy
    state.energy_remaining_min_kcal = remaining_energy_min
    state.energy_remaining_max_kcal = remaining_energy_max
    state.adherence_score = None
    state.confidence_score = None
    state.calculation_inputs = {
        "source": "servings",
        "window_start": window_start.isoformat(),
        "window_end": window_end.isoformat(),
        "serving_ids": [str(serving.id) for serving in servings],
        "serving_count": len(servings),
        "nutrition_target_id": (
            str(nutrition_target.id) if nutrition_target is not None else None
        ),
        "aggregation_policy": "consumed_else_served_else_planned_plus_explicit_assumptions",
        "assumptions": assumption_inputs or {},
    }
    state.computed_at = datetime.now(UTC)
    _apply_components(state, _build_components(servings, nutrition_target))

    return state
