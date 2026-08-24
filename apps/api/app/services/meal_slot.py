import uuid
from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.meal import MealEvent

ACTIVE_MEAL_SLOT_STATUSES = frozenset({"planned", "prepared", "served", "completed"})


class MealSlotConflictError(ValueError):
    pass


def assert_meal_slot_available(
    session: Session,
    *,
    family_id: uuid.UUID,
    family_timezone: str,
    scheduled_at: datetime,
    meal_type: str,
    exclude_event_id: uuid.UUID | None = None,
) -> None:
    if scheduled_at.tzinfo is None or scheduled_at.utcoffset() is None:
        raise ValueError("scheduled_at must be timezone-aware.")

    zone = ZoneInfo(family_timezone)
    local_date = scheduled_at.astimezone(zone).date()
    local_start = datetime.combine(local_date, time.min, tzinfo=zone).astimezone(UTC)
    local_end = (datetime.combine(local_date, time.min, tzinfo=zone) + timedelta(days=1)).astimezone(
        UTC
    )

    query = select(MealEvent.id).where(
        MealEvent.family_id == family_id,
        MealEvent.meal_type == meal_type,
        MealEvent.scheduled_at >= local_start,
        MealEvent.scheduled_at < local_end,
        MealEvent.status.in_(ACTIVE_MEAL_SLOT_STATUSES),
    )
    if exclude_event_id is not None:
        query = query.where(MealEvent.id != exclude_event_id)

    if session.scalar(query.limit(1)) is not None:
        raise MealSlotConflictError(
            "A meal is already planned for this meal slot on this date."
        )
