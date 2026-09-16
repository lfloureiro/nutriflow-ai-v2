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
from app.models.nutrition_constraint import NutritionConstraint
from app.models.nutrition_plan import NutritionPlan, NutritionPlanRule
from app.models.person import Person

PLANNING_DATE = date(2026, 9, 16)


def _override_db(db_session: Session):
    def override_get_db():
        yield db_session

    return override_get_db


def _food(
    family: Family,
    *,
    key: str,
    name: str,
    protein: str,
) -> FoodCompositionSnapshot:
    return FoodCompositionSnapshot(
        food_item=FoodItem(
            family=family,
            catalog_key=key,
            name=name,
            food_kind="dish",
            source="test",
            suitable_meal_types=["breakfast"],
        ),
        reference_quantity=Decimal("100.0000"),
        reference_unit="g",
        energy_kcal=Decimal("350.0000"),
        data_version="test-v1",
        source="test",
        effective_at=datetime(2026, 9, 16, 8, 0, tzinfo=UTC),
        nutrients=[
            FoodNutrientComponent(
                nutrient_key="protein",
                value=Decimal(protein),
                unit="g",
            )
        ],
    )


def test_scoped_recommendation_uses_plan_fit_before_preferences(db_session: Session) -> None:
    family = Family(name="Plan-Fit recommendation family", timezone="Europe/Lisbon")
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
        calculation_version="recommendation-plan-fit-test-v1",
    )
    low = _food(
        family,
        key="food:preferred-low-protein",
        name="Preferred low protein breakfast",
        protein="10.0000",
    )
    high = _food(
        family,
        key="food:plain-high-protein",
        name="Plain high protein breakfast",
        protein="20.0000",
    )
    person.food_preferences.append(
        FoodPreference(
            subject_type="food",
            subject_key="food:preferred-low-protein",
            preference_type="like",
            intensity=5,
            source="user",
        )
    )
    constraint = NutritionConstraint(
        person=person,
        constraint_type="meal_target",
        target_type="nutrient",
        target_key="protein",
        operator="min",
        value_min=Decimal("15.0000"),
        unit="g",
        severity="required",
        is_mandatory=True,
        source="nutritionist",
        start_date=PLANNING_DATE,
    )
    plan = NutritionPlan(
        person=person,
        lineage_id=uuid.uuid4(),
        version=1,
        title="Breakfast protein plan",
        source_type="nutritionist",
        source_name="Test nutritionist",
        status="active",
        valid_from=PLANNING_DATE,
        rules=[
            NutritionPlanRule(
                rule_kind="constraint",
                nutrition_constraint=constraint,
                meal_type="breakfast",
                priority=120,
                source_statement="Breakfast protein at least 15 g.",
                applies_outside_plan=False,
            )
        ],
    )
    db_session.add_all([family, state, low, high, plan])
    db_session.flush()

    assert person.id is not None
    assert state.id is not None
    assert low.id is not None
    assert high.id is not None
    payload = {
        "daily_nutrition_state_id": str(state.id),
        "planning_date": PLANNING_DATE.isoformat(),
        "meal_type": "breakfast",
        "candidates": [
            {
                "candidate_kind": "food_item",
                "composition_id": str(low.id),
                "quantity": "100.0000",
                "quantity_unit": "g",
            },
            {
                "candidate_kind": "food_item",
                "composition_id": str(high.id),
                "quantity": "100.0000",
                "quantity_unit": "g",
            },
        ],
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
    assert body["engine_version"] == "meal-recommendation-plan-fit-v1"
    assert [option["candidate_key"] for option in body["options"]] == [
        "food:plain-high-protein",
        "food:preferred-low-protein",
    ]

    eligible = body["options"][0]
    blocked = body["options"][1]
    assert eligible["eligible"] is True
    assert eligible["score_breakdown"]["plan_fit"] == "1.0000"
    assert blocked["eligible"] is False
    assert blocked["rank"] is None
    assert "plan_fit_rule:meal:nutrient:protein:fail" in blocked["exclusion_reasons"]
    assert "plan_fit_status:fail" in blocked["exclusion_reasons"]
