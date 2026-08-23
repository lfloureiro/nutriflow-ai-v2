from dataclasses import dataclass, replace
from decimal import ROUND_HALF_UP, Decimal

from app.models.daily_nutrition_state import DailyNutritionState
from app.services.meal_recommendation import (
    MealCandidate,
    build_food_candidate,
    build_recipe_candidate,
)

POLICY_VERSION = "meal-energy-allocation-v2"
PORTION_VERSION = "portion-sizing-v1"
ZERO = Decimal(0)
ONE = Decimal(1)
ENERGY_QUANTUM = Decimal("0.01")
QUANTITY_QUANTUM = Decimal("0.0001")
PORTION_STEP = Decimal("0.25")
MIN_PORTION_FACTOR = Decimal("0.50")
MAX_PORTION_FACTOR = Decimal("2.00")

MEAL_ENERGY_WEIGHTS: dict[str, Decimal] = {
    "breakfast": Decimal("0.25"),
    "lunch": Decimal("0.35"),
    "snack": Decimal("0.10"),
    "dinner": Decimal("0.30"),
}
MEAL_SEQUENCE = tuple(MEAL_ENERGY_WEIGHTS)


class MealEnergyAllocationError(ValueError):
    pass


@dataclass(frozen=True)
class MealEnergyAllocation:
    meal_type: str
    weight: Decimal
    remaining_weight: Decimal
    daily_target_min_kcal: Decimal | None
    daily_target_max_kcal: Decimal | None
    meal_target_min_kcal: Decimal | None
    meal_target_max_kcal: Decimal | None
    policy_version: str = POLICY_VERSION


@dataclass(frozen=True)
class PortionSizingResult:
    candidate: MealCandidate
    allocation: MealEnergyAllocation
    portion_factor: Decimal


def _q_energy(value: Decimal) -> Decimal:
    return value.quantize(ENERGY_QUANTUM, rounding=ROUND_HALF_UP)


def _spent_energy(state: DailyNutritionState) -> Decimal:
    return (
        state.energy_consumed_kcal
        + state.energy_planned_kcal
        + (state.energy_assumed_kcal or ZERO)
    )


def _daily_target(
    state: DailyNutritionState,
    remaining: Decimal | None,
) -> Decimal | None:
    if remaining is None:
        return None
    return _q_energy(_spent_energy(state) + remaining)


def _positive_remaining(value: Decimal | None) -> Decimal | None:
    if value is None:
        return None
    return max(value, ZERO)


def _remaining_weight(meal_type: str) -> Decimal:
    try:
        start = MEAL_SEQUENCE.index(meal_type)
    except ValueError as exc:
        raise MealEnergyAllocationError(
            f"Unsupported meal type for energy allocation: {meal_type!r}."
        ) from exc
    return sum(
        (MEAL_ENERGY_WEIGHTS[item] for item in MEAL_SEQUENCE[start:]),
        start=ZERO,
    )


def _meal_target_from_remaining(
    remaining: Decimal | None,
    *,
    weight: Decimal,
    remaining_weight: Decimal,
) -> Decimal | None:
    positive = _positive_remaining(remaining)
    if positive is None:
        return None
    if remaining_weight <= ZERO:
        raise MealEnergyAllocationError("Remaining meal weight must be positive.")
    return _q_energy(positive * weight / remaining_weight)


def allocate_meal_energy(
    state: DailyNutritionState,
    *,
    meal_type: str,
) -> MealEnergyAllocation:
    try:
        weight = MEAL_ENERGY_WEIGHTS[meal_type]
    except KeyError as exc:
        raise MealEnergyAllocationError(
            f"Unsupported meal type for energy allocation: {meal_type!r}."
        ) from exc

    remaining_weight = _remaining_weight(meal_type)
    daily_min = _daily_target(state, state.energy_remaining_min_kcal)
    daily_max = _daily_target(state, state.energy_remaining_max_kcal)
    meal_min = _meal_target_from_remaining(
        state.energy_remaining_min_kcal,
        weight=weight,
        remaining_weight=remaining_weight,
    )
    meal_max = _meal_target_from_remaining(
        state.energy_remaining_max_kcal,
        weight=weight,
        remaining_weight=remaining_weight,
    )
    if meal_min is not None and meal_max is not None and meal_min > meal_max:
        meal_min = meal_max

    return MealEnergyAllocation(
        meal_type=meal_type,
        weight=weight,
        remaining_weight=remaining_weight,
        daily_target_min_kcal=daily_min,
        daily_target_max_kcal=daily_max,
        meal_target_min_kcal=meal_min,
        meal_target_max_kcal=meal_max,
    )


def _target_midpoint(allocation: MealEnergyAllocation) -> Decimal | None:
    minimum = allocation.meal_target_min_kcal
    maximum = allocation.meal_target_max_kcal
    if minimum is not None and maximum is not None:
        return (minimum + maximum) / Decimal(2)
    return minimum if minimum is not None else maximum


def _round_portion_factor(value: Decimal) -> Decimal:
    clamped = min(MAX_PORTION_FACTOR, max(MIN_PORTION_FACTOR, value))
    steps = (clamped / PORTION_STEP).quantize(Decimal(1), rounding=ROUND_HALF_UP)
    rounded = steps * PORTION_STEP
    return min(MAX_PORTION_FACTOR, max(MIN_PORTION_FACTOR, rounded))


def _rebuild_candidate(candidate: MealCandidate, *, quantity: Decimal) -> MealCandidate:
    if candidate.food_composition is not None:
        return build_food_candidate(
            candidate.food_composition,
            quantity=quantity,
            quantity_unit=candidate.quantity_unit,
        )
    if candidate.recipe_composition is not None:
        return build_recipe_candidate(
            candidate.recipe_composition,
            quantity=quantity,
            quantity_unit=candidate.quantity_unit,
        )
    raise MealEnergyAllocationError(
        f"Candidate {candidate.key!r} does not retain a composition for portion sizing."
    )


def _with_allocation(
    candidate: MealCandidate,
    *,
    allocation: MealEnergyAllocation,
    portion_factor: Decimal,
) -> MealCandidate:
    return replace(
        candidate,
        portion_factor=portion_factor,
        meal_energy_target_min_kcal=allocation.meal_target_min_kcal,
        meal_energy_target_max_kcal=allocation.meal_target_max_kcal,
        energy_allocation_policy=allocation.policy_version,
    )


def size_candidate_for_meal(
    candidate: MealCandidate,
    state: DailyNutritionState,
    *,
    meal_type: str,
) -> PortionSizingResult:
    allocation = allocate_meal_energy(state, meal_type=meal_type)
    target = _target_midpoint(allocation)
    energy = candidate.nutrition.energy_kcal

    if target is None or energy is None or energy <= ZERO or target <= ZERO:
        return PortionSizingResult(
            candidate=_with_allocation(
                candidate,
                allocation=allocation,
                portion_factor=ONE,
            ),
            allocation=allocation,
            portion_factor=ONE,
        )

    factor = _round_portion_factor(target / energy)
    quantity = (candidate.quantity * factor).quantize(
        QUANTITY_QUANTUM,
        rounding=ROUND_HALF_UP,
    )
    resized = _rebuild_candidate(candidate, quantity=quantity)
    return PortionSizingResult(
        candidate=_with_allocation(
            resized,
            allocation=allocation,
            portion_factor=factor,
        ),
        allocation=allocation,
        portion_factor=factor,
    )


def size_candidates_for_meal(
    candidates: list[MealCandidate],
    state: DailyNutritionState,
    *,
    meal_type: str,
) -> tuple[list[MealCandidate], MealEnergyAllocation, dict[str, Decimal]]:
    allocation = allocate_meal_energy(state, meal_type=meal_type)
    resized: list[MealCandidate] = []
    factors: dict[str, Decimal] = {}
    for candidate in candidates:
        result = size_candidate_for_meal(candidate, state, meal_type=meal_type)
        resized.append(result.candidate)
        factors[candidate.key] = result.portion_factor
    return resized, allocation, factors
