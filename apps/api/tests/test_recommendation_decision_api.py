import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.main import app
from app.models.family import Family
from app.models.food_catalog import FoodCompositionSnapshot, FoodItem, FoodNutrientComponent
from app.models.meal import MealEvent
from app.models.person import Person
from app.models.recommendation_feedback import (
    MealRecommendationFeedback,
    MealRecommendationOption,
    MealRecommendationRun,
)


def _override_db(db_session: Session):
    def override_get_db():
        yield db_session

    return override_get_db


def _persisted_option(
    db_session: Session,
    *,
    eligible: bool = True,
) -> MealRecommendationOption:
    family = Family(name="Decision API Family", timezone="Europe/Lisbon")
    person = Person(
        family=family,
        first_name="Ana",
        preferred_locale="pt-PT",
        timezone="Europe/Lisbon",
    )
    food = FoodItem(
        family=family,
        catalog_key="family:decision:chicken",
        name="Chicken bowl",
        food_kind="dish",
        source="test",
    )
    composition = FoodCompositionSnapshot(
        food_item=food,
        reference_quantity=Decimal("100.0000"),
        reference_unit="g",
        energy_kcal=Decimal("200.0000"),
        data_version="test-v1",
        source="test",
        effective_at=datetime(2026, 8, 22, tzinfo=UTC),
        nutrients=[
            FoodNutrientComponent(
                nutrient_key="protein",
                value=Decimal("10.0000"),
                unit="g",
            )
        ],
    )
    run = MealRecommendationRun(
        person=person,
        planning_date=date(2026, 8, 22),
        meal_type="dinner",
        engine_version="meal-recommendation-v1",
    )
    option = MealRecommendationOption(
        recommendation_run=run,
        food_item=food,
        food_composition_snapshot=composition,
        candidate_key=food.catalog_key,
        candidate_name=food.name,
        candidate_kind="food_item",
        quantity=Decimal("250.0000"),
        quantity_unit="g",
        eligible=eligible,
        rank=1 if eligible else None,
        score=Decimal("2.5000") if eligible else None,
        score_breakdown={"energy": "1.0000"} if eligible else {},
        exclusion_reasons=[] if eligible else ["mandatory_test_exclusion"],
        explanation=["candidate_fits_remaining_energy"] if eligible else ["excluded"],
        candidate_subjects=[{"type": "dish", "key": food.catalog_key}],
        nutrition_snapshot={
            "energy_kcal": "500.00",
            "nutrients": {"protein": {"value": "25.0000", "unit": "g"}},
        },
    )
    db_session.add(family)
    db_session.flush()
    return option


def test_accept_decision_creates_planned_meal_and_feedback(db_session: Session) -> None:
    option = _persisted_option(db_session)
    app.dependency_overrides[get_db] = _override_db(db_session)
    try:
        with TestClient(app) as client:
            response = client.post(
                f"/api/recommendation-options/{option.id}/decision",
                json={
                    "action": "accepted",
                    "scheduled_at": "2026-08-22T19:30:00+00:00",
                    "timezone": "Europe/Lisbon",
                    "location": "Home",
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    body = response.json()
    assert body["recommendation_option_id"] == str(option.id)
    assert body["action"] == "accepted"
    assert body["meal_event_id"] is not None
    assert body["resulting_serving_id"] is not None
    assert body["meal_event_status"] == "planned"
    assert body["quantity_planned"] == "250.0000"
    assert body["quantity_unit"] == "g"
    assert body["energy_planned_kcal"] == "500.00"

    events = db_session.scalars(select(MealEvent)).all()
    feedback = db_session.scalars(select(MealRecommendationFeedback)).all()
    assert len(events) == 1
    assert len(feedback) == 1
    assert feedback[0].action == "accepted"


def test_modified_decision_recalculates_planned_nutrition(db_session: Session) -> None:
    option = _persisted_option(db_session)
    app.dependency_overrides[get_db] = _override_db(db_session)
    try:
        with TestClient(app) as client:
            response = client.post(
                f"/api/recommendation-options/{option.id}/decision",
                json={
                    "action": "modified",
                    "scheduled_at": "2026-08-22T20:00:00+00:00",
                    "timezone": "Europe/Lisbon",
                    "quantity": "150.0000",
                    "feedback_metadata": {"reason": "smaller_portion"},
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    body = response.json()
    assert body["action"] == "modified"
    assert body["quantity_planned"] == "150.0000"
    assert body["energy_planned_kcal"] == "300.00"

    feedback = db_session.scalars(select(MealRecommendationFeedback)).one()
    assert feedback.feedback_metadata == {"reason": "smaller_portion"}


def test_rejected_decision_records_feedback_without_meal(db_session: Session) -> None:
    option = _persisted_option(db_session)
    app.dependency_overrides[get_db] = _override_db(db_session)
    try:
        with TestClient(app) as client:
            response = client.post(
                f"/api/recommendation-options/{option.id}/decision",
                json={
                    "action": "rejected",
                    "feedback_metadata": {"reason": "not_today"},
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    body = response.json()
    assert body["action"] == "rejected"
    assert body["meal_event_id"] is None
    assert body["resulting_serving_id"] is None
    assert db_session.scalars(select(MealEvent)).all() == []

    feedback = db_session.scalars(select(MealRecommendationFeedback)).one()
    assert feedback.action == "rejected"
    assert feedback.feedback_metadata == {"reason": "not_today"}


def test_decision_api_returns_not_found_for_unknown_option(db_session: Session) -> None:
    app.dependency_overrides[get_db] = _override_db(db_session)
    try:
        with TestClient(app) as client:
            response = client.post(
                f"/api/recommendation-options/{uuid.uuid4()}/decision",
                json={"action": "rejected"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["detail"] == "Recommendation option not found."


def test_decision_api_rejects_materialization_of_ineligible_option(
    db_session: Session,
) -> None:
    option = _persisted_option(db_session, eligible=False)
    app.dependency_overrides[get_db] = _override_db(db_session)
    try:
        with TestClient(app) as client:
            response = client.post(
                f"/api/recommendation-options/{option.id}/decision",
                json={
                    "action": "accepted",
                    "scheduled_at": "2026-08-22T19:30:00+00:00",
                    "timezone": "Europe/Lisbon",
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    assert response.json()["detail"] == (
        "An ineligible recommendation option cannot create a planned meal."
    )


def test_rejected_decision_cannot_include_meal_planning_fields(db_session: Session) -> None:
    option = _persisted_option(db_session)
    app.dependency_overrides[get_db] = _override_db(db_session)
    try:
        with TestClient(app) as client:
            response = client.post(
                f"/api/recommendation-options/{option.id}/decision",
                json={
                    "action": "rejected",
                    "scheduled_at": "2026-08-22T19:30:00+00:00",
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    assert response.json()["detail"] == (
        "Rejected recommendation decisions cannot include meal-planning fields."
    )
