from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

_CACHE_KEY = "nutriflow.weekly_planning_request_cache"


@dataclass
class WeeklyPlanningRequestCache:
    daily_states: dict[tuple[object, object], Any] = field(default_factory=dict)
    effective_plans: dict[tuple[object, object, str], Any] = field(default_factory=dict)
    weekly_progress: dict[tuple[object, object], Any] = field(default_factory=dict)
    candidate_profiles: dict[tuple[object, str, object], Any] = field(default_factory=dict)
    transformable_recipes: dict[tuple[object, object], bool] = field(default_factory=dict)


def current_weekly_planning_cache(session: Session) -> WeeklyPlanningRequestCache | None:
    cache = session.info.get(_CACHE_KEY)
    return cache if isinstance(cache, WeeklyPlanningRequestCache) else None


@contextmanager
def weekly_planning_cache_scope(session: Session):
    existing = current_weekly_planning_cache(session)
    if existing is not None:
        yield existing
        return

    cache = WeeklyPlanningRequestCache()
    session.info[_CACHE_KEY] = cache
    try:
        yield cache
    finally:
        session.info.pop(_CACHE_KEY, None)
