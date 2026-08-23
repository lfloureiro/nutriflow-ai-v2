from collections.abc import Iterable

from app.models.meal_candidate_planning_profile import MealCandidatePlanningProfile

VALID_MEAL_TYPES = frozenset({"breakfast", "lunch", "snack", "dinner"})
MAIN_MEAL_TYPES = ("lunch", "dinner")


class MealSuitabilityError(ValueError):
    pass


def normalize_meal_types(
    values: Iterable[str] | None,
    *,
    defaults: tuple[str, ...],
) -> tuple[str, ...]:
    if values is None:
        return defaults
    result = tuple(dict.fromkeys(values))
    invalid = [meal_type for meal_type in result if meal_type not in VALID_MEAL_TYPES]
    if invalid:
        raise MealSuitabilityError(f"Invalid meal types: {invalid!r}.")
    return result


def resolve_meal_types(
    *,
    profile: MealCandidatePlanningProfile | None,
    catalogue_meal_types: Iterable[str] | None,
    defaults: tuple[str, ...],
) -> tuple[str, ...]:
    """Resolve Family override -> catalogue classification -> legacy fallback."""
    catalogue = normalize_meal_types(catalogue_meal_types, defaults=defaults)
    if profile is None:
        return catalogue
    if not profile.auto_plan_enabled:
        return ()
    return normalize_meal_types(profile.suitable_meal_types, defaults=catalogue)


def food_default_meal_types(food_kind: str) -> tuple[str, ...]:
    return MAIN_MEAL_TYPES if food_kind == "dish" else ()
