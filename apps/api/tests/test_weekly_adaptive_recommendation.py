import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.main import app
from app.models.daily_nutrition_state import DailyNutritionState
from app.models.family import Family
from app.models.food_catalog import FoodCompositionSnapshot, FoodItem, FoodNutrientComponent
from app.models.food_preference import FoodPreference
from app.models.meal import MealEvent, MealParticipant, Serving
from app.models.meal_candidate_planning_profile import MealCandidatePlanningProfile
from app.models.person import Person
from app.schemas.nutrition_plan import (
    NutritionPlanCreate,
    NutritionPlanGuidelineCreate,
    NutritionPlanUpdate,
)
from app.services.nutrition_plan import (
    add_nutrition_plan_guideline,
    create_nutrition_plan,
    update_nutrition_plan,
)

PLANNING_DATE = date(2026, 9, 17)


def _override_db(db_session: Session):
    def override_get_db():
        yield db_session

    return override_get_db


def _setup_person(db_session: Session) -> tuple[Family, Person, DailyNutritionState]:
    family = Family(name="Weekly adaptive family", timezone="Europe/Lisbon")
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
        energy_consumed_kcal=Decimal("0.00"),
        energy_planned_kcal=Decimal("0.00"),
        calculation_version="weekly-adaptive-test-v1",
    )
    db_session.add_all([family, state])
    db_session.flush()
    return family, person, state


def _food(
    db_session: Session,
    *,
    family: Family,
    key: str,
    name: str,
    primary_protein: str | None,
) -> FoodCompositionSnapshot:
    item = FoodItem(
        family_id=family.id,
        catalog_key=key,
        name=name,
        food_kind="dish",
        source="test",
        suitable_meal_types=["lunch"],
        is_active=True,
    )
    composition = FoodCompositionSnapshot(
        food_item=item,
        reference_quantity=Decimal("100.0000"),
        reference_unit="g",
        energy_kcal=Decimal("400.0000"),
        data_version=f"{key}-v1",
        source="test",
        effective_at=datetime(2026, 9, 1, 12, 0, tzinfo=UTC),
        nutrients=[
            FoodNutrientComponent(
                nutrient_key="protein",
                value=Decimal("25.0000"),
                unit="g",
            )
        ],
    )
    db_session.add(composition)
    db_session.flush()
    if primary_protein is not None:
        db_session.add(
            MealCandidatePlanningProfile(
                family_id=family.id,
                food_item_id=item.id,
                recipe_id=None,
                candidate_kind="food_item",
                planning_category="main",
                primary_protein=primary_protein,
                suitable_meal_types=["lunch"],
                auto_plan_enabled=True,
                source="test",
            )
        )
        db_session.flush()
    return composition


def _activate_frequency_guideline(
    db_session: Session,
    *,
    person: Person,
    target_key: str,
    minimum: int | None = None,
    maximum: int | None = None,
    mandatory: bool = True,
) -> None:
    plan = create_nutrition_plan(
        db_session,
        person=person,
        data=NutritionPlanCreate(
            title="Weekly adaptive guidance",
            source_type="nutritionist",
            source_name="Dietitian",
            valid_from=date(2026, 9, 1),
        ),
    )
    add_nutrition_plan_guideline(
        db_session,
        plan=plan,
        data=NutritionPlanGuidelineCreate(
            guideline_type="frequency",
            target_type="food_category",
            target_key=target_key,
            description=f"Weekly frequency for {target_key}",
            period="week",
            minimum_occurrences=minimum,
            maximum_occurrences=maximum,
            is_mandatory=mandatory,
            priority=120,
        ),
    )
    update_nutrition_plan(
        db_session,
        plan=plan,
        data=NutritionPlanUpdate(status="active"),
    )


def _planned_meal(
    db_session: Session,
    *,
    family: Family,
    person: Person,
    food_item: FoodItem,
    scheduled_at: datetime,
) -> None:
    event = MealEvent(
        family_id=family.id,
        meal_type="lunch",
        scheduled_at=scheduled_at,
        timezone="Europe/Lisbon",
        status="planned",
        source="test",
    )
    participant = MealParticipant(
        meal_event=event,
        person_id=person.id,
        status="planned",
    )
    participant.servings.append(
        Serving(
            food_item_id=food_item.id,
            recipe_id=None,
            item_type="dish",
            item_key=food_item.catalog_key,
            item_name=food_item.name,
            status="planned",
            nutrition_source="estimated",
        )
    )
    db_session.add(event)
    db_session.flush()


def _candidate_payload(composition: FoodCompositionSnapshot) -> dict[str, str]:
    assert composition.id is not None
    return {
        "candidate_kind": "food_item",
        "composition_id": str(composition.id),
        "quantity": "100.0000",
        "quantity_unit": "g",
    }


def test_weekly_minimum_support_reranks_without_becoming_a_per_meal_gate(
    db_session: Session,
) -> None:
    family, person, state = _setup_person(db_session)
    fish = _food(
        db_session,
        family=family,
        key="dish:fish",
        name="Fish lunch",
        primary_protein="fish",
    )
    beef = _food(
        db_session,
        family=family,
        key="dish:beef",
        name="Beef lunch",
        primary_protein="red_meat",
    )
    _activate_frequency_guideline(
        db_session,
        person=person,
        target_key="fish",
        minimum=3,
        mandatory=True,
    )
    person.food_preferences.append(
        FoodPreference(
            subject_type="food",
            subject_key="dish:beef",
            preference_type="like",
            intensity=5,
            source="user",
        )
    )
    db_session.commit()

    assert person.id is not None
    assert state.id is not None
    payload = {
        "daily_nutrition_state_id": str(state.id),
        "planning_date": PLANNING_DATE.isoformat(),
        "meal_type": "lunch",
        "candidates": [_candidate_payload(beef), _candidate_payload(fish)],
    }

    app.dependency_overrides[get_db] = _override_db(db_session)
    try:
        with TestClient(app) as client:
            response = client.post(
                f"/api/persons/{person.id}/meal-recommendations",
                json=payload,
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    body = response.json()
    assert body["engine_version"].endswith("+weekly-frequency-v1")
    assert [option["candidate_key"] for option in body["options"]] == [
        "dish:fish",
        "dish:beef",
    ]
    fish_option, beef_option = body["options"]
    assert fish_option["eligible"] is True
    assert beef_option["eligible"] is True
    assert any(
        item == "weekly_frequency_support:mandatory:1"
        for item in fish_option["explanation"]
    )


def test_mandatory_weekly_maximum_blocks_candidate_through_meal_plan_fit(
    db_session: Session,
) -> None:
    family, person, state = _setup_person(db_session)
    fish = _food(
        db_session,
        family=family,
        key="dish:fish-max",
        name="Fish lunch",
        primary_protein="fish",
    )
    beef = _food(
        db_session,
        family=family,
        key="dish:beef-max",
        name="Beef lunch",
        primary_protein="red_meat",
    )
    _activate_frequency_guideline(
        db_session,
        person=person,
        target_key="fish",
        maximum=1,
        mandatory=True,
    )
    assert fish.food_item is not None
    _planned_meal(
        db_session,
        family=family,
        person=person,
        food_item=fish.food_item,
        scheduled_at=datetime(2026, 9, 15, 13, 0, tzinfo=UTC),
    )
    db_session.commit()

    assert person.id is not None
    assert state.id is not None
    fit_payload = {
        "daily_nutrition_state_id": str(state.id),
        "planning_date": PLANNING_DATE.isoformat(),
        "meal_type": "lunch",
        "candidate": _candidate_payload(fish),
    }
    recommendation_payload = {
        "daily_nutrition_state_id": str(state.id),
        "planning_date": PLANNING_DATE.isoformat(),
        "meal_type": "lunch",
        "candidates": [_candidate_payload(fish), _candidate_payload(beef)],
    }

    app.dependency_overrides[get_db] = _override_db(db_session)
    try:
        with TestClient(app) as client:
            fit_response = client.post(
                f"/api/persons/{person.id}/meal-plan-fit",
                json=fit_payload,
            )
            recommendation_response = client.post(
                f"/api/persons/{person.id}/meal-recommendations",
                json=recommendation_payload,
            )
    finally:
        app.dependency_overrides.clear()

    assert fit_response.status_code == 200
    fit = fit_response.json()
    assert fit["eligible"] is False
    frequency = next(
        item for item in fit["guideline_results"] if item["guideline_type"] == "frequency"
    )
    assert frequency["current_occurrences"] == 1
    assert frequency["projected_occurrences"] == 2
    assert frequency["status"] == "fail"
    assert "primary_protein" in frequency["matched_by"]

    assert recommendation_response.status_code == 201
    recommendation = recommendation_response.json()
    by_key = {option["candidate_key"]: option for option in recommendation["options"]}
    assert by_key["dish:fish-max"]["eligible"] is False
    assert (
        "plan_fit_guideline:frequency:food_category:fish:fail"
        in by_key["dish:fish-max"]["exclusion_reasons"]
    )
    assert by_key["dish:beef-max"]["eligible"] is True


def test_mandatory_weekly_maximum_fails_closed_when_lower_bound_is_unsafe(
    db_session: Session,
) -> None:
    family, person, state = _setup_person(db_session)
    fish = _food(
        db_session,
        family=family,
        key="dish:fish-uncertain",
        name="Fish lunch",
        primary_protein="fish",
    )
    unknown = _food(
        db_session,
        family=family,
        key="dish:unknown-weekly",
        name="Unclassified lunch",
        primary_protein=None,
    )
    _activate_frequency_guideline(
        db_session,
        person=person,
        target_key="fish",
        maximum=2,
        mandatory=True,
    )
    assert fish.food_item is not None
    assert unknown.food_item is not None
    _planned_meal(
        db_session,
        family=family,
        person=person,
        food_item=fish.food_item,
        scheduled_at=datetime(2026, 9, 15, 13, 0, tzinfo=UTC),
    )
    _planned_meal(
        db_session,
        family=family,
        person=person,
        food_item=unknown.food_item,
        scheduled_at=datetime(2026, 9, 16, 13, 0, tzinfo=UTC),
    )
    db_session.commit()

    assert person.id is not None
    assert state.id is not None
    payload = {
        "daily_nutrition_state_id": str(state.id),
        "planning_date": PLANNING_DATE.isoformat(),
        "meal_type": "lunch",
        "candidate": _candidate_payload(fish),
    }

    app.dependency_overrides[get_db] = _override_db(db_session)
    try:
        with TestClient(app) as client:
            response = client.post(
                f"/api/persons/{person.id}/meal-plan-fit",
                json=payload,
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["eligible"] is False
    frequency = next(
        item for item in body["guideline_results"] if item["guideline_type"] == "frequency"
    )
    assert frequency["current_occurrences"] == 1
    assert frequency["projected_occurrences"] == 2
    assert frequency["counts_are_lower_bound"] is True
    assert frequency["status"] == "unknown"
