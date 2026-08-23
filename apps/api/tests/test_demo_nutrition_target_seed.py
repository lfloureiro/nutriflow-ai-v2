from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.demo_nutrition_target_seed import seed_demo_nutrition_targets
from app.demo_seed import DEMO_PERSON_ID, seed_demo_dataset
from app.models.nutrition_target import NutritionTarget
from app.services.planning_bootstrap_api import get_planning_bootstrap

NOW = datetime(2026, 8, 23, 9, 0, tzinfo=UTC)


def test_demo_nutrition_targets_cover_all_people_and_future_planning(db_session: Session) -> None:
    seed_demo_dataset(db_session, now=NOW)
    result = seed_demo_nutrition_targets(db_session, now=NOW)
    db_session.flush()

    assert result.target_count == 4
    assert result.state_count == 4

    targets = list(db_session.scalars(select(NutritionTarget)).all())
    assert len(targets) == 4

    primary = next(target for target in targets if target.person_id == DEMO_PERSON_ID)
    assert primary.energy_min_kcal == Decimal("1800.00")
    assert primary.energy_max_kcal == Decimal("2000.00")
    assert primary.estimated_tdee_kcal == Decimal("2220.00")

    today = get_planning_bootstrap(
        db_session,
        person_id=DEMO_PERSON_ID,
        scheduled_at=NOW,
        ensure_state=True,
    )
    assert today.daily_nutrition_state is not None
    assert today.daily_nutrition_state.energy_consumed_kcal == Decimal("1000.00")
    assert today.daily_nutrition_state.energy_planned_kcal == Decimal("0.00")
    assert today.daily_nutrition_state.energy_remaining_min_kcal == Decimal("800.00")
    assert today.daily_nutrition_state.energy_remaining_max_kcal == Decimal("1000.00")

    future = get_planning_bootstrap(
        db_session,
        person_id=DEMO_PERSON_ID,
        scheduled_at=NOW + timedelta(days=2),
        ensure_state=True,
    )
    assert future.daily_nutrition_state is not None
    assert future.daily_nutrition_state.energy_consumed_kcal == Decimal("0.00")
    assert future.daily_nutrition_state.energy_planned_kcal == Decimal("0.00")
    assert future.daily_nutrition_state.energy_assumed_kcal == Decimal("350.00")
    assert future.daily_nutrition_state.energy_remaining_min_kcal == Decimal("1450.00")
    assert future.daily_nutrition_state.energy_remaining_max_kcal == Decimal("1650.00")
