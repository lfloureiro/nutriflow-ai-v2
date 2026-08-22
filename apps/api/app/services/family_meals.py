import uuid
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.family import Family
from app.models.meal import MealEvent, MealParticipant
from app.schemas.family_meals import (
    FamilyMealDetailParticipantRead,
    FamilyMealDetailRead,
    FamilyMealParticipantRead,
    FamilyMealRead,
    FamilyMealsDayRead,
    FamilyMealServingRead,
    FamilyMealsRead,
)

ACTIVE_FAMILY_MEAL_STATUSES = frozenset({"planned", "prepared", "served", "completed"})


def _family_local_date(family: Family, start_date: date | None) -> date:
    if start_date is not None:
        return start_date
    return datetime.now(UTC).astimezone(ZoneInfo(family.timezone)).date()


def _utc_range_bounds(
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


def build_family_meals(
    db: Session,
    family: Family,
    *,
    start_date: date | None = None,
    day_count: int = 7,
) -> FamilyMealsRead:
    first_date = _family_local_date(family, start_date)
    start_at, end_at = _utc_range_bounds(family, first_date, day_count)
    family_timezone = ZoneInfo(family.timezone)

    meals = db.scalars(
        select(MealEvent)
        .options(
            selectinload(MealEvent.participants).selectinload(MealParticipant.person),
        )
        .where(
            MealEvent.family_id == family.id,
            MealEvent.scheduled_at >= start_at,
            MealEvent.scheduled_at < end_at,
            MealEvent.status.in_(ACTIVE_FAMILY_MEAL_STATUSES),
        )
        .order_by(MealEvent.scheduled_at, MealEvent.id)
    ).all()

    meals_by_date: dict[date, list[FamilyMealRead]] = {
        first_date + timedelta(days=offset): [] for offset in range(day_count)
    }

    for meal in meals:
        local_date = meal.scheduled_at.astimezone(family_timezone).date()
        meals_by_date[local_date].append(
            FamilyMealRead(
                id=meal.id,
                meal_type=meal.meal_type,
                title=meal.title,
                scheduled_at=meal.scheduled_at,
                timezone=meal.timezone,
                status=meal.status,
                location=meal.location,
                participants=[
                    FamilyMealParticipantRead(
                        person_id=participant.person_id,
                        first_name=participant.person.first_name,
                        last_name=participant.person.last_name,
                        status=participant.status,
                    )
                    for participant in meal.participants
                ],
            )
        )

    return FamilyMealsRead(
        family_id=family.id,
        family_name=family.name,
        timezone=family.timezone,
        start_date=first_date,
        end_date=first_date + timedelta(days=day_count - 1),
        days=[
            FamilyMealsDayRead(date=day_date, meals=meals_by_date[day_date])
            for day_date in meals_by_date
        ],
    )


def build_family_meal_detail(
    db: Session,
    family: Family,
    meal_event_id: uuid.UUID,
) -> FamilyMealDetailRead | None:
    meal = db.scalar(
        select(MealEvent)
        .options(
            selectinload(MealEvent.participants).selectinload(MealParticipant.person),
            selectinload(MealEvent.participants).selectinload(MealParticipant.servings),
        )
        .where(
            MealEvent.family_id == family.id,
            MealEvent.id == meal_event_id,
        )
    )
    if meal is None:
        return None

    return FamilyMealDetailRead(
        family_id=family.id,
        family_name=family.name,
        timezone=family.timezone,
        id=meal.id,
        meal_type=meal.meal_type,
        title=meal.title,
        scheduled_at=meal.scheduled_at,
        status=meal.status,
        location=meal.location,
        participants=[
            FamilyMealDetailParticipantRead(
                person_id=participant.person_id,
                first_name=participant.person.first_name,
                last_name=participant.person.last_name,
                status=participant.status,
                servings=[
                    FamilyMealServingRead(
                        id=serving.id,
                        item_type=serving.item_type,
                        item_name=serving.item_name,
                        status=serving.status,
                        quantity_planned=serving.quantity_planned,
                        quantity_served=serving.quantity_served,
                        quantity_consumed=serving.quantity_consumed,
                        quantity_unit=serving.quantity_unit,
                        energy_planned_kcal=serving.energy_planned_kcal,
                        energy_served_kcal=serving.energy_served_kcal,
                        energy_consumed_kcal=serving.energy_consumed_kcal,
                    )
                    for serving in participant.servings
                ],
            )
            for participant in meal.participants
        ],
    )
