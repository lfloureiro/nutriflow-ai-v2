import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.main import app
from app.models.daily_nutrition_state import DailyNutritionState, DailyNutritionStateComponent
from app.models.family import Family
from app.models.food_catalog import FoodCompositionSnapshot, FoodItem, FoodNutrientComponent
from app.models.nutrition_constraint import NutritionConstraint
from app.models.person import Person
from app.models.recommendation_feedback import MealRecommendationRun

PLANNING_DATE = date(2026, 8, 22)


def _override_db(db_session: Session):
    def override_get_db():
        yield db_session

    return override_get_db


def _family_person(db_session: Session, *, family_name: str = "API Family") -> tuple[Family, Person]:
    family = Family(name=family_name, timezone="Europe/Lisbon")
    person = Person(
        family=family,
        first_name="Ana",
        preferred_locale="pt-PT",
        timezone="Europe/Lisbon",
    )
    db_session.add(family)
    db_session.flush()
    return family, person


def _daily_state(db_session: Session, person: Person) -> DailyNutritionState:
    state = DailyNutritionState(
        person=person,
        state_date=PLANNING_DATE,
        timezone="Europe/Lisbon",
        energy_consumed_kcal=Decimal("900.00"),
        energy_planned_kcal=Decimal("300.00"),
        energy_remaining_min_kcal=Decimal("500.00"),
        energy_remaining_max_kcal=Decimal("800.00"),
        calculation_version="test-api-v1",
        components=[
            DailyNutritionStateComponent(
                target_type="nutrient",
                target_key="sodium",
                consumed_value=Decimal("800.0000"),
                planned_value=Decimal("0.0000"),
                remaining_max=Decimal("200.0000"),
                unit="mg",
            )
        ],
    )
    db_session.add(state)
    db_session.flush()
    return state


def _food_composition(
    db_session: Session,
    family: Family,
    *,
    key: str,
    name: str,
    sodium: str,
) -> FoodCompositionSnapshot:
    item = FoodItem(
        family=family,
        catalog_key=key,
        name=name,
        food_kind="dish",
        source="test",
    )
    composition = FoodCompositionSnapshot(
        food_item=item,
        reference_quantity=Decimal("100.0000"),
        reference_unit="g",
        energy_kcal=Decimal("400.0000"),
        data_version="test-v1",
        source="test",
        effective_at=datetime(2026, 8, 22, tzinfo=UTC),
        nutrients=[
            FoodNutrientComponent(
                nutrient_key="sodium",
                value=Decimal(sodium),
                unit="mg",
            )
        ],
    )
    db_session.add(composition)
    db_session.flush()
    return composition


def _request_payload(state: DailyNutritionState, composition_ids: list[uuid.UUID]) -> dict[str, object]:
    if state.id is None:
        raise AssertionError("Daily state must be persisted.")
    return {
        "daily_nutrition_state_id": str(state.id),
        "planning_date": PLANNING_DATE.isoformat(),
        "meal_type": "lunch",
        "candidates": [
            {
                "candidate_kind": "food_item",
                "composition_id": str(composition_id),
                "quantity": "100.0000",
                "quantity_unit": "g",
            }
            for composition_id in composition_ids
        ],
    }


def test_meal_recommendation_api_persists_ranked_and_excluded_options(
    db_session: Session,
) -> None:
    family, person = _family_person(db_session)
    state = _daily_state(db_session, person)
    person.nutrition_constraints.append(
        NutritionConstraint(
            constraint_type="nutrient_limit",
            target_type="nutrient",
            target_key="sodium",
            operator="max",
            value_max=Decimal("1000.0000"),
            unit="mg",
            severity="required",
            is_mandatory=True,
            source="doctor",
        )
    )
    safe = _food_composition(
        db_session,
        family,
        key="food:api-safe",
        name="Safe dish",
        sodium="100.0000",
    )
    high = _food_composition(
        db_session,
        family,
        key="food:api-high",
        name="High sodium dish",
        sodium="350.0000",
    )
    db_session.flush()

    app.dependency_overrides[get_db] = _override_db(db_session)
    try:
        with TestClient(app) as client:
            response = client.post(
                f"/api/persons/{person.id}/meal-recommendations",
                json=_request_payload(state, [high.id, safe.id]),
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    body = response.json()
    assert body["person_id"] == str(person.id)
    assert body["daily_nutrition_state_id"] == str(state.id)
    assert body["engine_version"] == "meal-recommendation-v1"
    assert [option["candidate_key"] for option in body["options"]] == [
        "food:api-safe",
        "food:api-high",
    ]
    assert body["options"][0]["eligible"] is True
    assert body["options"][0]["rank"] == 1
    assert body["options"][1]["eligible"] is False
    assert body["options"][1]["exclusion_reasons"] == ["mandatory_nutrient_max:sodium"]

    runs = db_session.scalars(select(MealRecommendationRun)).all()
    assert len(runs) == 1
    assert runs[0].person_id == person.id
    assert len(runs[0].options) == 2


def test_meal_recommendation_api_rejects_state_from_another_person(
    db_session: Session,
) -> None:
    family, person = _family_person(db_session)
    other = Person(
        family=family,
        first_name="Bruno",
        preferred_locale="pt-PT",
        timezone="Europe/Lisbon",
    )
    db_session.add(other)
    db_session.flush()
    state = _daily_state(db_session, other)
    composition = _food_composition(
        db_session,
        family,
        key="food:state-owner",
        name="State owner dish",
        sodium="50.0000",
    )

    app.dependency_overrides[get_db] = _override_db(db_session)
    try:
        with TestClient(app) as client:
            response = client.post(
                f"/api/persons/{person.id}/meal-recommendations",
                json=_request_payload(state, [composition.id]),
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    assert response.json()["detail"] == "DailyNutritionState belongs to a different Person."


def test_meal_recommendation_api_rejects_cross_family_candidate(
    db_session: Session,
) -> None:
    _, person = _family_person(db_session)
    state = _daily_state(db_session, person)
    other_family = Family(name="Other Family", timezone="Europe/Lisbon")
    db_session.add(other_family)
    db_session.flush()
    composition = _food_composition(
        db_session,
        other_family,
        key="food:other-family",
        name="Other family dish",
        sodium="50.0000",
    )

    app.dependency_overrides[get_db] = _override_db(db_session)
    try:
        with TestClient(app) as client:
            response = client.post(
                f"/api/persons/{person.id}/meal-recommendations",
                json=_request_payload(state, [composition.id]),
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    assert "belongs to another Family" in response.json()["detail"]


def test_meal_recommendation_api_returns_not_found_for_unknown_composition(
    db_session: Session,
) -> None:
    _, person = _family_person(db_session)
    state = _daily_state(db_session, person)

    app.dependency_overrides[get_db] = _override_db(db_session)
    try:
        with TestClient(app) as client:
            response = client.post(
                f"/api/persons/{person.id}/meal-recommendations",
                json=_request_payload(state, [uuid.uuid4()]),
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["detail"] == "Food composition snapshot not found."


def test_meal_recommendation_api_rejects_duplicate_catalogue_candidate_keys(
    db_session: Session,
) -> None:
    family, person = _family_person(db_session)
    state = _daily_state(db_session, person)
    composition = _food_composition(
        db_session,
        family,
        key="food:duplicate",
        name="Duplicate dish",
        sodium="50.0000",
    )

    app.dependency_overrides[get_db] = _override_db(db_session)
    try:
        with TestClient(app) as client:
            response = client.post(
                f"/api/persons/{person.id}/meal-recommendations",
                json=_request_payload(state, [composition.id, composition.id]),
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    assert response.json()["detail"] == (
        "Recommendation candidates must have unique catalogue keys."
    )


def test_meal_recommendation_api_rejects_unsafe_candidate_quantity_unit(
    db_session: Session,
) -> None:
    family, person = _family_person(db_session)
    state = _daily_state(db_session, person)
    composition = _food_composition(
        db_session,
        family,
        key="food:unsafe-unit",
        name="Unsafe unit dish",
        sodium="50.0000",
    )
    payload = _request_payload(state, [composition.id])
    candidates = payload["candidates"]
    if not isinstance(candidates, list):
        raise AssertionError("Candidate payload must be a list.")
    candidates[0]["quantity_unit"] = "ml"

    app.dependency_overrides[get_db] = _override_db(db_session)
    try:
        with TestClient(app) as client:
            response = client.post(
                f"/api/persons/{person.id}/meal-recommendations",
                json=payload,
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    assert response.json()["detail"] == "Cannot scale food candidate using quantity unit 'ml'."
