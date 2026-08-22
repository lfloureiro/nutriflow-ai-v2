from datetime import UTC, datetime
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.demo_seed import (
    DEMO_CALCULATION_VERSION,
    DEMO_FAMILY_ID,
    DEMO_FOODS,
    DEMO_INES_ID,
    DEMO_MEALS,
    DEMO_PEOPLE,
    DEMO_PERSON_ID,
    DEMO_RUI_ID,
    seed_demo_dataset,
)
from app.main import app
from app.models.daily_health_state import DailyHealthState
from app.models.daily_nutrition_state import DailyNutritionState
from app.models.family import Family
from app.models.food_catalog import FoodCompositionSnapshot, FoodItem
from app.models.meal import MealEvent, MealParticipant
from app.models.person import Person
from app.services.meal_recommendation import build_food_candidate, recommend_meals

NOW = datetime(2026, 8, 22, 9, 30, tzinfo=UTC)


def _override_db(db_session: Session):
    def override_get_db():
        yield db_session

    return override_get_db


def test_demo_seed_is_idempotent_and_scoped(db_session: Session) -> None:
    unrelated = Family(name="Unrelated family", timezone="Europe/Lisbon")
    db_session.add(unrelated)
    db_session.flush()
    unrelated_id = unrelated.id

    first = seed_demo_dataset(db_session, now=NOW)
    second = seed_demo_dataset(db_session, now=NOW)
    db_session.flush()

    assert first == second
    assert first.family_id == DEMO_FAMILY_ID
    assert first.person_id == DEMO_PERSON_ID
    assert first.candidate_count == len(DEMO_FOODS)
    assert first.member_count == len(DEMO_PEOPLE)
    assert first.meal_count == len(DEMO_MEALS)
    assert db_session.get(Family, unrelated_id) is not None

    demo_family_count = db_session.scalar(
        select(func.count()).select_from(Family).where(Family.id == DEMO_FAMILY_ID)
    )
    demo_person_count = db_session.scalar(
        select(func.count()).select_from(Person).where(Person.family_id == DEMO_FAMILY_ID)
    )
    demo_food_count = db_session.scalar(
        select(func.count()).select_from(FoodItem).where(
            FoodItem.family_id == DEMO_FAMILY_ID,
            FoodItem.catalog_key.startswith("demo:"),
        )
    )
    demo_state_count = db_session.scalar(
        select(func.count()).select_from(DailyNutritionState).where(
            DailyNutritionState.person_id == DEMO_PERSON_ID,
            DailyNutritionState.state_date == first.planning_date,
            DailyNutritionState.calculation_version == DEMO_CALCULATION_VERSION,
        )
    )
    demo_health_count = db_session.scalar(
        select(func.count()).select_from(DailyHealthState).where(
            DailyHealthState.person_id.in_([definition.id for definition in DEMO_PEOPLE]),
            DailyHealthState.state_date == first.planning_date,
        )
    )
    demo_meal_count = db_session.scalar(
        select(func.count()).select_from(MealEvent).where(
            MealEvent.family_id == DEMO_FAMILY_ID,
            MealEvent.source == "demo",
        )
    )
    demo_participant_count = db_session.scalar(
        select(func.count())
        .select_from(MealParticipant)
        .join(MealEvent)
        .where(
            MealEvent.family_id == DEMO_FAMILY_ID,
            MealEvent.source == "demo",
        )
    )

    assert demo_family_count == 1
    assert demo_person_count == len(DEMO_PEOPLE)
    assert demo_food_count == len(DEMO_FOODS)
    assert demo_state_count == 1
    assert demo_health_count == 4
    assert demo_meal_count == len(DEMO_MEALS)
    assert demo_participant_count == 10


def test_demo_seed_is_visible_through_planning_bootstrap(db_session: Session) -> None:
    result = seed_demo_dataset(db_session, now=NOW)
    db_session.flush()

    app.dependency_overrides[get_db] = _override_db(db_session)
    try:
        with TestClient(app) as client:
            response = client.get(
                f"/api/persons/{result.person_id}/planning-bootstrap",
                params={"scheduled_at": NOW.isoformat()},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["family_id"] == str(DEMO_FAMILY_ID)
    assert body["daily_nutrition_state"]["id"] == str(result.daily_nutrition_state_id)
    assert len(body["candidates"]) == len(DEMO_FOODS)
    assert {candidate["name"] for candidate in body["candidates"]} == {
        definition.name for definition in DEMO_FOODS
    }


def test_demo_seed_populates_family_dashboard_variation(db_session: Session) -> None:
    result = seed_demo_dataset(db_session, now=NOW)
    db_session.flush()

    app.dependency_overrides[get_db] = _override_db(db_session)
    try:
        with TestClient(app) as client:
            response = client.get(
                f"/api/families/{DEMO_FAMILY_ID}/dashboard",
                params={"on_date": result.planning_date.isoformat()},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert len(body["members"]) == len(DEMO_PEOPLE)
    assert len(body["meals"]) == len(DEMO_MEALS)

    members = {member["person_id"]: member for member in body["members"]}
    primary = members[str(DEMO_PERSON_ID)]
    rui = members[str(DEMO_RUI_ID)]
    ines = members[str(DEMO_INES_ID)]

    assert primary["nutrition"]["energy_consumed_kcal"] == "1000.00"
    assert primary["health"]["latest_weight_kg"] == "103.000"
    assert primary["health"]["steps"] == 3800
    assert rui["health"]["steps"] == 10300
    assert rui["health"]["latest_weight_kg"] is None
    assert ines["nutrition"] is None
    assert ines["health"]["sleep_duration_minutes"] is None

    meals = {meal["meal_type"]: meal for meal in body["meals"]}
    assert meals["breakfast"]["status"] == "completed"
    assert len(meals["breakfast"]["participant_person_ids"]) == 4
    assert len(meals["lunch"]["participant_person_ids"]) == 2
    assert len(meals["dinner"]["participant_person_ids"]) == 4


def test_demo_seed_exercises_ranking_and_mandatory_exclusion(db_session: Session) -> None:
    result = seed_demo_dataset(db_session, now=NOW)
    db_session.flush()

    person = db_session.get(Person, result.person_id)
    daily_state = db_session.get(DailyNutritionState, result.daily_nutrition_state_id)
    assert person is not None
    assert daily_state is not None

    snapshots = db_session.scalars(
        select(FoodCompositionSnapshot)
        .join(FoodItem)
        .where(FoodItem.family_id == DEMO_FAMILY_ID, FoodItem.catalog_key.startswith("demo:"))
        .order_by(FoodItem.catalog_key)
    ).all()
    candidates = [
        build_food_candidate(
            snapshot,
            quantity=snapshot.reference_quantity,
            quantity_unit=snapshot.reference_unit,
        )
        for snapshot in snapshots
    ]

    recommendation = recommend_meals(
        daily_state=daily_state,
        candidates=candidates,
        preferences=list(person.food_preferences),
        adverse_reactions=list(person.food_adverse_reactions),
        constraints=list(person.nutrition_constraints),
        planning_date=result.planning_date,
    )

    by_key = {evaluation.candidate.key: evaluation for evaluation in recommendation.evaluations}
    assert by_key["demo:pizza-pepperoni"].eligible is False
    assert by_key["demo:pizza-pepperoni"].exclusion_reasons == (
        "mandatory_nutrient_max:sodium",
    )
    assert by_key["demo:massa-bolonhesa"].eligible is True
    assert "preferred:dish:demo:massa-bolonhesa" in by_key[
        "demo:massa-bolonhesa"
    ].explanation
    assert by_key["demo:frango-arroz-legumes"].score is not None
    assert by_key["demo:frango-arroz-legumes"].score > Decimal(0)
