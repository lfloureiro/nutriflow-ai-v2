import uuid
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.daily_health_state import DailyHealthState
from app.models.daily_nutrition_state import DailyNutritionState
from app.models.family import Family
from app.models.meal import MealEvent
from app.models.person import Person
from app.schemas.family_dashboard import (
    FamilyDashboardHealthRead,
    FamilyDashboardMealRead,
    FamilyDashboardMemberRead,
    FamilyDashboardNutritionRead,
    FamilyDashboardRead,
)

ACTIVE_DASHBOARD_MEAL_STATUSES = frozenset({"planned", "prepared", "served", "completed"})


def _dashboard_date(family: Family, on_date: date | None) -> date:
    if on_date is not None:
        return on_date
    return datetime.now(UTC).astimezone(ZoneInfo(family.timezone)).date()


def _utc_day_bounds(family: Family, dashboard_date: date) -> tuple[datetime, datetime]:
    timezone = ZoneInfo(family.timezone)
    local_start = datetime.combine(dashboard_date, time.min, tzinfo=timezone)
    local_end = local_start + timedelta(days=1)
    return local_start.astimezone(UTC), local_end.astimezone(UTC)


def _latest_health_by_person(
    db: Session,
    person_ids: list[uuid.UUID],
    dashboard_date: date,
) -> dict[uuid.UUID, DailyHealthState]:
    if not person_ids:
        return {}
    states = db.scalars(
        select(DailyHealthState)
        .where(
            DailyHealthState.person_id.in_(person_ids),
            DailyHealthState.state_date == dashboard_date,
        )
        .order_by(DailyHealthState.person_id, DailyHealthState.computed_at.desc())
    ).all()
    latest: dict[uuid.UUID, DailyHealthState] = {}
    for state in states:
        latest.setdefault(state.person_id, state)
    return latest


def _latest_nutrition_by_person(
    db: Session,
    person_ids: list[uuid.UUID],
    dashboard_date: date,
) -> dict[uuid.UUID, DailyNutritionState]:
    if not person_ids:
        return {}
    states = db.scalars(
        select(DailyNutritionState)
        .where(
            DailyNutritionState.person_id.in_(person_ids),
            DailyNutritionState.state_date == dashboard_date,
        )
        .order_by(DailyNutritionState.person_id, DailyNutritionState.computed_at.desc())
    ).all()
    latest: dict[uuid.UUID, DailyNutritionState] = {}
    for state in states:
        latest.setdefault(state.person_id, state)
    return latest


def _health_read(state: DailyHealthState | None) -> FamilyDashboardHealthRead | None:
    if state is None:
        return None
    return FamilyDashboardHealthRead(
        state_date=state.state_date,
        latest_weight_kg=state.latest_weight_kg,
        weight_trend_7d_kg=state.weight_trend_7d_kg,
        weight_trend_28d_kg=state.weight_trend_28d_kg,
        steps=state.steps,
        active_energy_kcal=state.active_energy_kcal,
        sleep_duration_minutes=state.sleep_duration_minutes,
        resting_heart_rate_bpm=state.resting_heart_rate_bpm,
        hrv_ms=state.hrv_ms,
        training_load=state.training_load,
        confidence_score=state.confidence_score,
        computed_at=state.computed_at,
    )


def _nutrition_read(
    state: DailyNutritionState | None,
) -> FamilyDashboardNutritionRead | None:
    if state is None:
        return None
    return FamilyDashboardNutritionRead(
        state_date=state.state_date,
        energy_consumed_kcal=state.energy_consumed_kcal,
        energy_planned_kcal=state.energy_planned_kcal,
        energy_remaining_min_kcal=state.energy_remaining_min_kcal,
        energy_remaining_max_kcal=state.energy_remaining_max_kcal,
        adherence_score=state.adherence_score,
        confidence_score=state.confidence_score,
        computed_at=state.computed_at,
    )


def build_family_dashboard(
    db: Session,
    family: Family,
    *,
    on_date: date | None = None,
) -> FamilyDashboardRead:
    dashboard_date = _dashboard_date(family, on_date)
    people = db.scalars(
        select(Person)
        .where(Person.family_id == family.id)
        .order_by(Person.first_name, Person.last_name, Person.id)
    ).all()
    person_ids = [person.id for person in people]

    health_by_person = _latest_health_by_person(db, person_ids, dashboard_date)
    nutrition_by_person = _latest_nutrition_by_person(db, person_ids, dashboard_date)

    start_at, end_at = _utc_day_bounds(family, dashboard_date)
    meals = db.scalars(
        select(MealEvent)
        .options(selectinload(MealEvent.participants))
        .where(
            MealEvent.family_id == family.id,
            MealEvent.scheduled_at >= start_at,
            MealEvent.scheduled_at < end_at,
            MealEvent.status.in_(ACTIVE_DASHBOARD_MEAL_STATUSES),
        )
        .order_by(MealEvent.scheduled_at, MealEvent.id)
    ).all()

    return FamilyDashboardRead(
        family_id=family.id,
        family_name=family.name,
        timezone=family.timezone,
        dashboard_date=dashboard_date,
        members=[
            FamilyDashboardMemberRead(
                person_id=person.id,
                first_name=person.first_name,
                last_name=person.last_name,
                timezone=person.timezone,
                health=_health_read(health_by_person.get(person.id)),
                nutrition=_nutrition_read(nutrition_by_person.get(person.id)),
            )
            for person in people
        ],
        meals=[
            FamilyDashboardMealRead(
                id=meal.id,
                meal_type=meal.meal_type,
                title=meal.title,
                scheduled_at=meal.scheduled_at,
                timezone=meal.timezone,
                status=meal.status,
                location=meal.location,
                participant_person_ids=[participant.person_id for participant in meal.participants],
            )
            for meal in meals
        ],
    )
