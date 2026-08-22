import uuid
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.family import Family
from app.models.food_catalog import Recipe
from app.models.meal import MealEvent, MealParticipant, Serving
from app.models.person import Person
from app.schemas.family_meal_plan import (
    MEAL_TYPES,
    FamilyMealPlanRead,
    MealPlanDayRead,
    MealPlanEntryCreate,
    MealPlanEntryRead,
    MealPlanEntryUpdate,
    MealPlanParticipantRead,
    MealPlanParticipantWrite,
    MealPlanSlotRead,
    MealType,
)
from app.services.recipe_catalogue import RecipeNotFoundError, get_family_recipe_model
from app.services.serving_nutrition import (
    ServingNutritionCalculationError,
    calculate_serving_nutrition,
)

ACTIVE_PLAN_STATUSES = frozenset({"planned", "prepared", "served", "completed"})


class MealPlanError(ValueError):
    pass


class MealPlanEntryNotFoundError(MealPlanError):
    pass


class MealPlanEntryLockedError(MealPlanError):
    pass


def _optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


def _first_date(family: Family, requested: date | None) -> date:
    if requested is not None:
        return requested
    return datetime.now(UTC).astimezone(ZoneInfo(family.timezone)).date()


def _range_bounds(
    family: Family,
    first_date: date,
    day_count: int,
) -> tuple[datetime, datetime]:
    timezone = ZoneInfo(family.timezone)
    local_start = datetime.combine(first_date, time.min, tzinfo=timezone)
    local_end = datetime.combine(
        first_date + timedelta(days=day_count),
        time.min,
        tzinfo=timezone,
    )
    return local_start.astimezone(UTC), local_end.astimezone(UTC)


def _event_options():
    return (
        selectinload(MealEvent.participants).selectinload(MealParticipant.person),
        selectinload(MealEvent.participants)
        .selectinload(MealParticipant.servings)
        .selectinload(Serving.recipe),
    )


def _event_recipe(event: MealEvent) -> Recipe | None:
    for participant in event.participants:
        for serving in participant.servings:
            if serving.recipe is not None:
                return serving.recipe
    return None


def _participant_serving(
    participant: MealParticipant,
    recipe_id: uuid.UUID | None,
) -> Serving | None:
    if recipe_id is not None:
        for serving in participant.servings:
            if serving.recipe_id == recipe_id:
                return serving
    return participant.servings[0] if participant.servings else None


def _entry_read(event: MealEvent, family_timezone: ZoneInfo) -> MealPlanEntryRead:
    recipe = _event_recipe(event)
    recipe_id = recipe.id if recipe is not None else None
    return MealPlanEntryRead(
        id=event.id,
        meal_type=event.meal_type,
        title=event.title,
        scheduled_at=event.scheduled_at,
        local_time=event.scheduled_at.astimezone(family_timezone).timetz().replace(tzinfo=None),
        status=event.status,
        recipe_id=recipe_id,
        recipe_name=recipe.name if recipe is not None else None,
        location=event.location,
        notes=event.notes,
        participants=[
            MealPlanParticipantRead(
                person_id=participant.person_id,
                first_name=participant.person.first_name,
                last_name=participant.person.last_name,
                quantity=serving.quantity_planned if serving is not None else None,
                unit=serving.quantity_unit if serving is not None else None,
                energy_kcal=serving.energy_planned_kcal if serving is not None else None,
            )
            for participant in event.participants
            for serving in [_participant_serving(participant, recipe_id)]
        ],
    )


def build_family_meal_plan(
    db: Session,
    family: Family,
    *,
    start_date: date | None = None,
    day_count: int = 7,
) -> FamilyMealPlanRead:
    first_date = _first_date(family, start_date)
    start_at, end_at = _range_bounds(family, first_date, day_count)
    family_timezone = ZoneInfo(family.timezone)

    events = db.scalars(
        select(MealEvent)
        .options(*_event_options())
        .where(
            MealEvent.family_id == family.id,
            MealEvent.scheduled_at >= start_at,
            MealEvent.scheduled_at < end_at,
            MealEvent.status.in_(ACTIVE_PLAN_STATUSES),
        )
        .order_by(MealEvent.scheduled_at, MealEvent.id)
    ).all()

    days: dict[date, dict[MealType, list[MealPlanEntryRead]]] = {
        first_date + timedelta(days=offset): {meal_type: [] for meal_type in MEAL_TYPES}
        for offset in range(day_count)
    }
    for event in events:
        local_date = event.scheduled_at.astimezone(family_timezone).date()
        if event.meal_type in MEAL_TYPES:
            days[local_date][event.meal_type].append(_entry_read(event, family_timezone))

    return FamilyMealPlanRead(
        family_id=family.id,
        family_name=family.name,
        timezone=family.timezone,
        start_date=first_date,
        end_date=first_date + timedelta(days=day_count - 1),
        days=[
            MealPlanDayRead(
                date=day_date,
                slots=[
                    MealPlanSlotRead(meal_type=meal_type, meals=slots[meal_type])
                    for meal_type in MEAL_TYPES
                ],
            )
            for day_date, slots in days.items()
        ],
    )


def _people_for_participants(
    db: Session,
    family_id: uuid.UUID,
    values: list[MealPlanParticipantWrite],
) -> dict[uuid.UUID, Person]:
    person_ids = [value.person_id for value in values]
    if len(person_ids) != len(set(person_ids)):
        raise MealPlanError("A Person can appear only once in one planned MealEvent.")
    people = db.scalars(
        select(Person).where(Person.family_id == family_id, Person.id.in_(person_ids))
    ).all()
    by_id = {person.id: person for person in people}
    missing = [person_id for person_id in person_ids if person_id not in by_id]
    if missing:
        raise MealPlanError("At least one participant does not belong to this Family.")
    return by_id


def _default_recipe_portion(recipe: Recipe) -> tuple[Decimal, str]:
    if (
        recipe.yield_quantity is not None
        and recipe.yield_unit is not None
        and recipe.serving_count is not None
    ):
        return recipe.yield_quantity / recipe.serving_count, recipe.yield_unit
    if recipe.serving_count is not None:
        return Decimal(1), "serving"
    if recipe.yield_quantity is not None and recipe.yield_unit is not None:
        return recipe.yield_quantity, recipe.yield_unit
    return Decimal(1), "recipe"


def _latest_recipe_composition(recipe: Recipe):
    return recipe.compositions[-1] if recipe.compositions else None


def _replace_participants(
    db: Session,
    event: MealEvent,
    family_id: uuid.UUID,
    recipe: Recipe,
    values: list[MealPlanParticipantWrite],
) -> None:
    people = _people_for_participants(db, family_id, values)
    event.participants.clear()
    db.flush()

    composition = _latest_recipe_composition(recipe)
    default_quantity, default_unit = _default_recipe_portion(recipe)

    for value in values:
        quantity = value.quantity if value.quantity is not None else default_quantity
        unit = value.unit.lower() if value.unit is not None else default_unit
        participant = MealParticipant(
            person=people[value.person_id],
            status="planned",
        )
        event.participants.append(participant)
        serving = Serving(
            recipe=recipe,
            item_type="recipe",
            item_key=recipe.recipe_key,
            item_name=recipe.name,
            status="planned",
            quantity_planned=quantity,
            quantity_unit=unit,
            nutrition_source="catalog" if composition is not None else "missing",
            source_reference="family-meal-plan",
        )
        if composition is not None:
            try:
                calculate_serving_nutrition(serving, composition)
            except ServingNutritionCalculationError as exc:
                raise MealPlanError(str(exc)) from exc
        participant.servings.append(serving)


def _scheduled_at(family: Family, on_date: date, local_time: time) -> datetime:
    return datetime.combine(on_date, local_time, tzinfo=ZoneInfo(family.timezone))


def create_meal_plan_entry(
    db: Session,
    family: Family,
    data: MealPlanEntryCreate,
) -> MealPlanEntryRead:
    try:
        recipe = get_family_recipe_model(db, family.id, data.recipe_id)
    except RecipeNotFoundError as exc:
        raise MealPlanError("Recipe not found for this Family.") from exc
    if not recipe.is_active:
        raise MealPlanError("Inactive recipes cannot be added to the plan.")

    event = MealEvent(
        family=family,
        meal_type=data.meal_type,
        title=recipe.name,
        scheduled_at=_scheduled_at(family, data.date, data.local_time),
        timezone=family.timezone,
        status="planned",
        location=_optional_text(data.location),
        source="user",
        source_reference="family-meal-plan",
        notes=_optional_text(data.notes),
    )
    db.add(event)
    db.flush()
    _replace_participants(db, event, family.id, recipe, data.participants)
    db.commit()
    event = _get_event(db, family.id, event.id)
    return _entry_read(event, ZoneInfo(family.timezone))


def _get_event(db: Session, family_id: uuid.UUID, meal_event_id: uuid.UUID) -> MealEvent:
    event = db.scalar(
        select(MealEvent)
        .options(*_event_options())
        .where(MealEvent.id == meal_event_id, MealEvent.family_id == family_id)
    )
    if event is None:
        raise MealPlanEntryNotFoundError("Meal plan entry not found")
    return event


def update_meal_plan_entry(
    db: Session,
    family: Family,
    meal_event_id: uuid.UUID,
    data: MealPlanEntryUpdate,
) -> MealPlanEntryRead:
    event = _get_event(db, family.id, meal_event_id)
    if event.status != "planned":
        raise MealPlanEntryLockedError("Only planned MealEvents can be edited.")

    fields = data.model_fields_set
    local = event.scheduled_at.astimezone(ZoneInfo(family.timezone))
    next_date = data.date if "date" in fields and data.date is not None else local.date()
    next_time = (
        data.local_time
        if "local_time" in fields and data.local_time is not None
        else local.timetz().replace(tzinfo=None)
    )
    if fields.intersection({"date", "local_time"}):
        event.scheduled_at = _scheduled_at(family, next_date, next_time)
    if "meal_type" in fields and data.meal_type is not None:
        event.meal_type = data.meal_type
    if "location" in fields:
        event.location = _optional_text(data.location)
    if "notes" in fields:
        event.notes = _optional_text(data.notes)

    current_recipe = _event_recipe(event)
    recipe = current_recipe
    recipe_changed = "recipe_id" in fields and data.recipe_id is not None
    if recipe_changed:
        try:
            recipe = get_family_recipe_model(db, family.id, data.recipe_id)
        except RecipeNotFoundError as exc:
            raise MealPlanError("Recipe not found for this Family.") from exc
        if not recipe.is_active:
            raise MealPlanError("Inactive recipes cannot be added to the plan.")
        event.title = recipe.name

    participants_changed = "participants" in fields and data.participants is not None
    if recipe_changed or participants_changed:
        if recipe is None:
            raise MealPlanError("A Recipe is required before participant portions can be edited.")
        if data.participants is not None:
            participant_values = data.participants
        else:
            participant_values = [
                MealPlanParticipantWrite(person_id=participant.person_id)
                for participant in event.participants
            ]
        _replace_participants(db, event, family.id, recipe, participant_values)

    db.commit()
    event = _get_event(db, family.id, meal_event_id)
    return _entry_read(event, ZoneInfo(family.timezone))


def cancel_meal_plan_entry(
    db: Session,
    family_id: uuid.UUID,
    meal_event_id: uuid.UUID,
) -> None:
    event = _get_event(db, family_id, meal_event_id)
    if event.status != "planned":
        raise MealPlanEntryLockedError("Only planned MealEvents can be removed from the plan.")
    event.status = "cancelled"
    db.commit()
