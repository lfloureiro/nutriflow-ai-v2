from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.main import app
from app.models.daily_nutrition_state import DailyNutritionState
from app.models.family import Family
from app.models.person import Person


def _override_db(db_session: Session):
    def override_get_db():
        yield db_session

    return override_get_db


def test_recommendation_bootstrap_can_materialize_missing_daily_state(
    db_session: Session,
) -> None:
    family = Family(name="Future planning family", timezone="Europe/Lisbon")
    person = Person(
        family=family,
        first_name="Ana",
        preferred_locale="pt-PT",
        timezone="Europe/Lisbon",
    )
    db_session.add(family)
    db_session.flush()

    app.dependency_overrides[get_db] = _override_db(db_session)
    try:
        with TestClient(app) as client:
            response = client.get(
                f"/api/persons/{person.id}/planning-bootstrap",
                params={
                    "scheduled_at": datetime(2026, 8, 25, 12, 0, tzinfo=UTC).isoformat(),
                    "ensure_state": "true",
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    state = response.json()["daily_nutrition_state"]
    assert state is not None
    assert state["state_date"] == "2026-08-25"
    assert state["calculation_version"] == "daily-nutrition-from-servings-v1"
    assert db_session.scalar(select(DailyNutritionState)) is not None
