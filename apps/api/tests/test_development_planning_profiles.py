from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.demo_seed import DEMO_FAMILY_ID, seed_demo_dataset
from app.development_planning_profile_seed import seed_development_planning_profiles
from app.legacy_v1_demo_seed import seed_legacy_v1_demo_catalog
from app.models.family import Family
from app.models.meal_candidate_planning_profile import MealCandidatePlanningProfile

NOW = datetime(2026, 8, 22, 18, 30, tzinfo=UTC)


def test_development_planning_profiles_are_idempotent(db_session: Session) -> None:
    seed_demo_dataset(db_session, now=NOW)
    family = db_session.get(Family, DEMO_FAMILY_ID)
    assert family is not None
    seed_legacy_v1_demo_catalog(db_session, family=family, now=NOW)

    first = seed_development_planning_profiles(db_session, family=family)
    second = seed_development_planning_profiles(db_session, family=family)
    db_session.flush()

    assert first == second
    assert first.profile_count == 11
    count = db_session.scalar(
        select(func.count())
        .select_from(MealCandidatePlanningProfile)
        .where(MealCandidatePlanningProfile.family_id == DEMO_FAMILY_ID)
    )
    assert count == 11

    profiles = db_session.scalars(
        select(MealCandidatePlanningProfile).where(
            MealCandidatePlanningProfile.family_id == DEMO_FAMILY_ID
        )
    ).all()
    assert all(profile.auto_plan_enabled for profile in profiles)
    assert all(profile.suitable_meal_types == ["lunch", "dinner"] for profile in profiles)
