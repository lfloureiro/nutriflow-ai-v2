from datetime import date

from sqlalchemy.orm import Session

from app.models.family import Family
from app.models.person import Person
from app.models.recommendation_feedback import MealRecommendationRun


def test_recommendation_run_accepts_composed_engine_version_longer_than_64_chars(
    db_session: Session,
) -> None:
    family = Family(name="Long engine version family", timezone="Europe/Lisbon")
    person = Person(
        family=family,
        first_name="Ana",
        preferred_locale="pt-PT",
        timezone="Europe/Lisbon",
    )
    engine_version = (
        "meal-recommendation-practical-v1+portion-sizing-v1+diversity-v1+feedback-v1"
    )
    assert len(engine_version) > 64

    run = MealRecommendationRun(
        person=person,
        planning_date=date(2026, 8, 24),
        meal_type="lunch",
        engine_version=engine_version,
    )
    db_session.add(run)
    db_session.flush()

    assert run.id is not None
    assert run.engine_version == engine_version
