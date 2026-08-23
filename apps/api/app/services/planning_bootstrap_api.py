import uuid
from datetime import datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.daily_nutrition_state import DailyNutritionState
from app.models.food_catalog import (
    FoodCompositionSnapshot,
    FoodItem,
    Recipe,
    RecipeCompositionSnapshot,
)
from app.models.meal import MealEvent, MealParticipant
from app.models.nutrition_target import NutritionTarget
from app.models.person import Person
from app.schemas.planning_bootstrap import (
    PlanningBootstrapRead,
    PlanningCandidateRead,
    PlanningDailyNutritionStateRead,
    PlanningNutritionComponentRead,
)
from app.services.daily_nutrition_state import recalculate_daily_nutrition_state

DEFAULT_STANDARD_BREAKFAST_KCAL = Decimal(350)
BREAKFAST_ASSUMPTION_CUTOFF = time(10, 0)


class PlanningBootstrapApiError(ValueError):
    pass


class PlanningBootstrapApiNotFoundError(PlanningBootstrapApiError):
    pass


def _validate_scheduled_at(scheduled_at: datetime) -> None:
    if scheduled_at.tzinfo is None or scheduled_at.utcoffset() is None:
        raise PlanningBootstrapApiError("scheduled_at must be timezone-aware.")


def _load_person(session: Session, person_id: uuid.UUID) -> Person:
    person = session.get(Person, person_id)
    if person is None:
        raise PlanningBootstrapApiNotFoundError("Person not found.")
    return person


def _planning_date(person: Person, scheduled_at: datetime):
    try:
        timezone = ZoneInfo(person.timezone)
    except ZoneInfoNotFoundError as exc:
        raise PlanningBootstrapApiError(
            f"Person has an unknown timezone: {person.timezone!r}."
        ) from exc
    return scheduled_at.astimezone(timezone).date()


def _latest_daily_state(
    session: Session,
    *,
    person_id: uuid.UUID,
    planning_date,
) -> DailyNutritionState | None:
    return session.scalar(
        select(DailyNutritionState)
        .where(
            DailyNutritionState.person_id == person_id,
            DailyNutritionState.state_date == planning_date,
        )
        .options(selectinload(DailyNutritionState.components))
        .order_by(
            DailyNutritionState.computed_at.desc(),
            DailyNutritionState.created_at.desc(),
            DailyNutritionState.id.desc(),
        )
        .limit(1)
    )


def _active_target(
    session: Session,
    *,
    person_id: uuid.UUID,
    planning_date,
) -> NutritionTarget | None:
    return session.scalar(
        select(NutritionTarget)
        .where(
            NutritionTarget.person_id == person_id,
            NutritionTarget.status == "active",
            NutritionTarget.valid_from <= planning_date,
            or_(NutritionTarget.valid_until.is_(None), NutritionTarget.valid_until >= planning_date),
        )
        .options(selectinload(NutritionTarget.components))
        .order_by(
            NutritionTarget.valid_from.desc(),
            NutritionTarget.created_at.desc(),
            NutritionTarget.id.desc(),
        )
        .limit(1)
    )


def _declared_breakfast(
    session: Session,
    *,
    person: Person,
    planning_date,
) -> bool:
    try:
        zone = ZoneInfo(person.timezone)
    except ZoneInfoNotFoundError as exc:
        raise PlanningBootstrapApiError(
            f"Person has an unknown timezone: {person.timezone!r}."
        ) from exc
    start = datetime.combine(planning_date, time.min, tzinfo=zone)
    end = start + timedelta(days=1)
    event_id = session.scalar(
        select(MealEvent.id)
        .join(MealParticipant, MealParticipant.meal_event_id == MealEvent.id)
        .where(
            MealParticipant.person_id == person.id,
            MealEvent.meal_type == "breakfast",
            MealEvent.scheduled_at >= start,
            MealEvent.scheduled_at < end,
            ~MealEvent.status.in_(("cancelled", "replaced")),
            MealParticipant.status != "replaced",
        )
        .limit(1)
    )
    return event_id is not None


def _breakfast_assumption(
    session: Session,
    *,
    person: Person,
    planning_date,
    scheduled_at: datetime,
) -> tuple[Decimal, dict[str, object]]:
    local_time = scheduled_at.astimezone(ZoneInfo(person.timezone)).time().replace(tzinfo=None)
    if local_time < BREAKFAST_ASSUMPTION_CUTOFF:
        return Decimal(0), {"standard_breakfast": {"applied": False, "reason": "before_cutoff"}}
    if _declared_breakfast(session, person=person, planning_date=planning_date):
        return Decimal(0), {"standard_breakfast": {"applied": False, "reason": "declared"}}

    configured = (
        person.profile.standard_breakfast_kcal
        if person.profile is not None and person.profile.standard_breakfast_kcal is not None
        else DEFAULT_STANDARD_BREAKFAST_KCAL
    )
    return configured, {
        "standard_breakfast": {
            "applied": configured > 0,
            "kcal": str(configured),
            "reason": "breakfast_not_declared",
            "cutoff_local_time": BREAKFAST_ASSUMPTION_CUTOFF.isoformat(timespec="minutes"),
            "source": (
                "person_profile"
                if person.profile is not None and person.profile.standard_breakfast_kcal is not None
                else "system_default"
            ),
        }
    }


def _ensure_daily_state(
    session: Session,
    *,
    person: Person,
    planning_date,
    scheduled_at: datetime,
) -> DailyNutritionState:
    target = _active_target(
        session,
        person_id=person.id,
        planning_date=planning_date,
    )
    assumed_energy, assumption_inputs = _breakfast_assumption(
        session,
        person=person,
        planning_date=planning_date,
        scheduled_at=scheduled_at,
    )
    state = recalculate_daily_nutrition_state(
        session,
        person=person,
        state_date=planning_date,
        timezone=person.timezone,
        nutrition_target=target,
        assumed_energy_kcal=assumed_energy,
        assumption_inputs=assumption_inputs,
    )
    session.commit()
    return state


def _preserve_synthetic_demo_state(state: DailyNutritionState) -> bool:
    inputs = state.calculation_inputs or {}
    return (
        state.calculation_version == "demo-energy-budget-v1"
        and inputs.get("source") == "synthetic-development-demo"
    )


def _daily_state_read(state: DailyNutritionState) -> PlanningDailyNutritionStateRead:
    if state.id is None:
        raise PlanningBootstrapApiError("DailyNutritionState must be persisted.")
    return PlanningDailyNutritionStateRead(
        id=state.id,
        state_date=state.state_date,
        timezone=state.timezone,
        energy_consumed_kcal=state.energy_consumed_kcal,
        energy_planned_kcal=state.energy_planned_kcal,
        energy_assumed_kcal=state.energy_assumed_kcal,
        energy_remaining_min_kcal=state.energy_remaining_min_kcal,
        energy_remaining_max_kcal=state.energy_remaining_max_kcal,
        calculation_version=state.calculation_version,
        computed_at=state.computed_at,
        components=[
            PlanningNutritionComponentRead(
                target_type=component.target_type,
                target_key=component.target_key,
                consumed_value=component.consumed_value,
                planned_value=component.planned_value,
                remaining_min=component.remaining_min,
                remaining_max=component.remaining_max,
                unit=component.unit,
            )
            for component in state.components
        ],
    )


def _food_candidates(
    session: Session,
    *,
    family_id: uuid.UUID,
    scheduled_at: datetime,
) -> list[PlanningCandidateRead]:
    snapshots = session.scalars(
        select(FoodCompositionSnapshot)
        .join(FoodItem)
        .where(
            FoodItem.is_active.is_(True),
            or_(FoodItem.family_id.is_(None), FoodItem.family_id == family_id),
            FoodCompositionSnapshot.effective_at <= scheduled_at,
        )
        .options(selectinload(FoodCompositionSnapshot.food_item))
        .order_by(
            FoodItem.catalog_key,
            FoodCompositionSnapshot.effective_at.desc(),
            FoodCompositionSnapshot.created_at.desc(),
            FoodCompositionSnapshot.id.desc(),
        )
    ).all()

    result: list[PlanningCandidateRead] = []
    seen: set[uuid.UUID] = set()
    for snapshot in snapshots:
        if snapshot.food_item_id in seen:
            continue
        seen.add(snapshot.food_item_id)
        if snapshot.id is None:
            raise PlanningBootstrapApiError("Food composition snapshot must be persisted.")
        food = snapshot.food_item
        result.append(
            PlanningCandidateRead(
                candidate_kind="food_item",
                composition_id=snapshot.id,
                catalog_key=food.catalog_key,
                name=food.name,
                category=food.food_kind,
                brand=food.brand,
                description=food.description,
                reference_quantity=snapshot.reference_quantity,
                reference_unit=snapshot.reference_unit,
                energy_kcal=snapshot.energy_kcal,
                composition_version=snapshot.data_version,
                composition_at=snapshot.effective_at,
            )
        )
    return result


def _recipe_candidate_quantity(
    recipe: Recipe,
    snapshot: RecipeCompositionSnapshot,
) -> Decimal:
    if recipe.serving_count is None:
        return snapshot.reference_quantity
    return snapshot.reference_quantity / recipe.serving_count


def _recipe_candidates(
    session: Session,
    *,
    family_id: uuid.UUID,
    scheduled_at: datetime,
) -> list[PlanningCandidateRead]:
    snapshots = session.scalars(
        select(RecipeCompositionSnapshot)
        .join(Recipe)
        .where(
            Recipe.is_active.is_(True),
            or_(Recipe.family_id.is_(None), Recipe.family_id == family_id),
            RecipeCompositionSnapshot.computed_at <= scheduled_at,
        )
        .options(selectinload(RecipeCompositionSnapshot.recipe))
        .order_by(
            Recipe.recipe_key,
            RecipeCompositionSnapshot.computed_at.desc(),
            RecipeCompositionSnapshot.created_at.desc(),
            RecipeCompositionSnapshot.id.desc(),
        )
    ).all()

    result: list[PlanningCandidateRead] = []
    seen: set[uuid.UUID] = set()
    for snapshot in snapshots:
        if snapshot.recipe_id in seen:
            continue
        seen.add(snapshot.recipe_id)
        if snapshot.id is None:
            raise PlanningBootstrapApiError("Recipe composition snapshot must be persisted.")
        recipe = snapshot.recipe
        result.append(
            PlanningCandidateRead(
                candidate_kind="recipe",
                composition_id=snapshot.id,
                catalog_key=recipe.recipe_key,
                name=recipe.name,
                category="recipe",
                brand=None,
                description=recipe.description,
                reference_quantity=_recipe_candidate_quantity(recipe, snapshot),
                reference_unit=snapshot.reference_unit,
                energy_kcal=(
                    snapshot.energy_kcal / recipe.serving_count
                    if snapshot.energy_kcal is not None and recipe.serving_count is not None
                    else snapshot.energy_kcal
                ),
                composition_version=snapshot.composition_version,
                composition_at=snapshot.computed_at,
            )
        )
    return result


def get_planning_bootstrap(
    session: Session,
    *,
    person_id: uuid.UUID,
    scheduled_at: datetime,
    ensure_state: bool = False,
) -> PlanningBootstrapRead:
    _validate_scheduled_at(scheduled_at)
    person = _load_person(session, person_id)
    planning_date = _planning_date(person, scheduled_at)
    state = _latest_daily_state(
        session,
        person_id=person_id,
        planning_date=planning_date,
    )
    if ensure_state and (state is None or not _preserve_synthetic_demo_state(state)):
        state = _ensure_daily_state(
            session,
            person=person,
            planning_date=planning_date,
            scheduled_at=scheduled_at,
        )
    candidates = _food_candidates(
        session,
        family_id=person.family_id,
        scheduled_at=scheduled_at,
    ) + _recipe_candidates(
        session,
        family_id=person.family_id,
        scheduled_at=scheduled_at,
    )
    candidates.sort(key=lambda candidate: (candidate.name.casefold(), candidate.catalog_key))

    return PlanningBootstrapRead(
        person_id=person.id,
        family_id=person.family_id,
        scheduled_at=scheduled_at,
        planning_date=planning_date,
        daily_nutrition_state=None if state is None else _daily_state_read(state),
        candidates=candidates,
    )
