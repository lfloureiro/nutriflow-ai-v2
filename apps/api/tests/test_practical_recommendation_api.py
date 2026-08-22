import uuid
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.main import app
from app.models.daily_nutrition_state import DailyNutritionState
from app.models.family import Family
from app.models.food_catalog import FoodCompositionSnapshot, FoodItem
from app.models.meal_candidate_availability import (
    MealCandidateAvailability,
    MealCommercialOffer,
    MealSourceOpeningWindow,
)
from app.models.person import Person
from app.models.recommendation_feedback import MealRecommendationRun
from app.models.schedule_entry import ScheduleEntry

PLANNING_DATE = date(2026, 8, 22)
SCHEDULED_AT = datetime(2026, 8, 22, 12, 0, tzinfo=UTC)


def _override_db(db_session: Session):
    def override_get_db():
        yield db_session

    return override_get_db


def _persist_base(
    db_session: Session,
    *,
    key: str,
) -> tuple[Family, Person, DailyNutritionState, FoodItem, FoodCompositionSnapshot]:
    family = Family(name=f"Practical API {key}", timezone="Europe/Lisbon")
    person = Person(
        family=family,
        first_name="Ana",
        preferred_locale="pt-PT",
        timezone="Europe/Lisbon",
    )
    state = DailyNutritionState(
        person=person,
        state_date=PLANNING_DATE,
        timezone="Europe/Lisbon",
        energy_consumed_kcal=Decimal("900.00"),
        energy_planned_kcal=Decimal("300.00"),
        energy_remaining_min_kcal=Decimal("300.00"),
        energy_remaining_max_kcal=Decimal("700.00"),
        calculation_version=f"test-practical-{key}",
    )
    food = FoodItem(
        family=family,
        catalog_key=f"food:practical:{key}",
        name=f"Practical dish {key}",
        food_kind="dish",
        source="test",
    )
    composition = FoodCompositionSnapshot(
        food_item=food,
        reference_quantity=Decimal("100.0000"),
        reference_unit="g",
        energy_kcal=Decimal("400.0000"),
        data_version="test-v1",
        source="test",
        effective_at=SCHEDULED_AT,
    )
    db_session.add_all([family, state, composition])
    db_session.flush()
    return family, person, state, food, composition


def _payload(
    state: DailyNutritionState,
    composition: FoodCompositionSnapshot,
    *,
    source_kinds: list[str],
    location: str | None = None,
    available_minutes: int | None = None,
) -> dict[str, object]:
    assert state.id is not None
    assert composition.id is not None
    return {
        "daily_nutrition_state_id": str(state.id),
        "planning_date": PLANNING_DATE.isoformat(),
        "scheduled_at": SCHEDULED_AT.isoformat(),
        "meal_type": "lunch",
        "location": location,
        "available_minutes": available_minutes,
        "has_kitchen": True,
        "source_kinds": source_kinds,
        "candidates": [
            {
                "candidate_kind": "food_item",
                "composition_id": str(composition.id),
                "quantity": "100.0000",
                "quantity_unit": "g",
            }
        ],
    }


def _post(
    db_session: Session,
    person: Person,
    payload: dict[str, object],
):
    app.dependency_overrides[get_db] = _override_db(db_session)
    try:
        with TestClient(app) as client:
            return client.post(
                f"/api/persons/{person.id}/meal-recommendations/practical",
                json=payload,
            )
    finally:
        app.dependency_overrides.clear()


def _availability(
    family: Family,
    food: FoodItem,
    *,
    source_kind: str,
    source_key: str,
    is_available: bool = True,
    location: str | None = None,
    preparation_minutes: int | None = None,
) -> MealCandidateAvailability:
    return MealCandidateAvailability(
        family=family,
        food_item=food,
        candidate_kind="food_item",
        source_kind=source_kind,
        source_key=source_key,
        is_available=is_available,
        location=location,
        preparation_minutes=preparation_minutes,
        requires_kitchen=False,
        source="test",
    )


def test_practical_api_uses_persisted_home_availability_and_persists_run(
    db_session: Session,
) -> None:
    family, person, state, food, composition = _persist_base(db_session, key="home")
    db_session.add(
        _availability(
            family,
            food,
            source_kind="home",
            source_key="home-kitchen",
            location="Home",
            preparation_minutes=5,
        )
    )
    db_session.flush()

    response = _post(
        db_session,
        person,
        _payload(
            state,
            composition,
            source_kinds=["home"],
            location="Home",
            available_minutes=15,
        ),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["engine_version"] == "meal-recommendation-practical-v1"
    assert body["options"][0]["eligible"] is True
    assert "planning_location:Home" in body["options"][0]["explanation"]
    assert body["commercial_offers"] == []

    run = db_session.scalar(select(MealRecommendationRun))
    assert run is not None
    assert run.context is not None
    assert run.context["entrypoint"] == "practical-api"
    assert run.context["source_kinds"] == ["home"]


def test_practical_api_schedule_unavailability_excludes_candidate(db_session: Session) -> None:
    _, person, state, _, composition = _persist_base(db_session, key="schedule")
    person.schedule_entries.append(
        ScheduleEntry(
            entry_type="one_off",
            event_type="meeting",
            availability_effect="unavailable",
            starts_at=SCHEDULED_AT - timedelta(minutes=30),
            ends_at=SCHEDULED_AT + timedelta(minutes=30),
            timezone="Europe/Lisbon",
            source="test",
        )
    )
    db_session.flush()

    response = _post(
        db_session,
        person,
        _payload(state, composition, source_kinds=["home"]),
    )

    assert response.status_code == 201
    option = response.json()["options"][0]
    assert option["eligible"] is False
    assert option["exclusion_reasons"] == ["schedule_unavailable"]


def test_practical_api_explicit_home_unavailability_excludes_candidate(
    db_session: Session,
) -> None:
    family, person, state, food, composition = _persist_base(db_session, key="home-off")
    db_session.add(
        _availability(
            family,
            food,
            source_kind="home",
            source_key="home-off",
            is_available=False,
        )
    )
    db_session.flush()

    response = _post(
        db_session,
        person,
        _payload(state, composition, source_kinds=["home"]),
    )

    assert response.status_code == 201
    assert response.json()["options"][0]["exclusion_reasons"] == [
        "candidate_unavailable"
    ]


def test_practical_api_pantry_only_requires_sufficient_stock(db_session: Session) -> None:
    _, person, state, _, composition = _persist_base(db_session, key="pantry-empty")

    response = _post(
        db_session,
        person,
        _payload(state, composition, source_kinds=["pantry"]),
    )

    assert response.status_code == 201
    assert response.json()["options"][0]["exclusion_reasons"] == [
        "candidate_unavailable"
    ]


def test_practical_api_any_available_source_keeps_candidate_eligible(db_session: Session) -> None:
    family, person, state, food, composition = _persist_base(db_session, key="source-or")
    db_session.add(
        _availability(
            family,
            food,
            source_kind="home",
            source_key="home-available",
        )
    )
    db_session.flush()

    response = _post(
        db_session,
        person,
        _payload(state, composition, source_kinds=["pantry", "home"]),
    )

    assert response.status_code == 201
    assert response.json()["options"][0]["eligible"] is True


def test_practical_api_respects_preparation_window(db_session: Session) -> None:
    family, person, state, food, composition = _persist_base(db_session, key="prep")
    db_session.add(
        _availability(
            family,
            food,
            source_kind="home",
            source_key="slow-home",
            preparation_minutes=30,
        )
    )
    db_session.flush()

    response = _post(
        db_session,
        person,
        _payload(
            state,
            composition,
            source_kinds=["home"],
            available_minutes=10,
        ),
    )

    assert response.status_code == 201
    assert response.json()["options"][0]["exclusion_reasons"] == [
        "preparation_time_exceeds_available_window"
    ]


def test_practical_api_returns_active_delivery_offer(db_session: Session) -> None:
    family, person, state, food, composition = _persist_base(db_session, key="delivery")
    delivery = _availability(
        family,
        food,
        source_kind="delivery",
        source_key="delivery-provider",
        location="Lisboa",
        preparation_minutes=20,
    )
    delivery.opening_windows.append(
        MealSourceOpeningWindow(
            weekday=5,
            local_start_time=time(12, 0),
            local_end_time=time(14, 0),
            timezone="Europe/Lisbon",
            source="test",
        )
    )
    delivery.commercial_offers.append(
        MealCommercialOffer(
            family=family,
            offer_key="offer-delivery",
            provider_key="provider-test",
            provider_name="Provider Test",
            item_price=Decimal("12.50"),
            currency="EUR",
            delivery_fee=Decimal("2.00"),
            minimum_order=Decimal("10.00"),
            is_available=True,
            observed_at=SCHEDULED_AT - timedelta(minutes=5),
            source="test",
        )
    )
    db_session.add(delivery)
    db_session.flush()

    response = _post(
        db_session,
        person,
        _payload(state, composition, source_kinds=["delivery"]),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["options"][0]["eligible"] is True
    assert len(body["commercial_offers"]) == 1
    offer = body["commercial_offers"][0]
    assert offer["offer_key"] == "offer-delivery"
    assert Decimal(offer["total_known_price"]) == Decimal("14.50")


def test_practical_api_closed_commercial_source_excludes_candidate(db_session: Session) -> None:
    family, person, state, food, composition = _persist_base(db_session, key="closed")
    delivery = _availability(
        family,
        food,
        source_kind="delivery",
        source_key="closed-delivery",
    )
    delivery.opening_windows.append(
        MealSourceOpeningWindow(
            weekday=5,
            local_start_time=time(8, 0),
            local_end_time=time(9, 0),
            timezone="Europe/Lisbon",
            source="test",
        )
    )
    db_session.add(delivery)
    db_session.flush()

    response = _post(
        db_session,
        person,
        _payload(state, composition, source_kinds=["delivery"]),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["options"][0]["exclusion_reasons"] == ["candidate_unavailable"]
    assert body["commercial_offers"] == []


def test_practical_api_missing_source_evidence_remains_unknown_not_excluded(
    db_session: Session,
) -> None:
    _, person, state, _, composition = _persist_base(db_session, key="unknown")

    response = _post(
        db_session,
        person,
        _payload(state, composition, source_kinds=["delivery"]),
    )

    assert response.status_code == 201
    assert response.json()["options"][0]["eligible"] is True
