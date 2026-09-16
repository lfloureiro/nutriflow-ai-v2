import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.main import app
from app.models.daily_nutrition_state import DailyNutritionState
from app.models.family import Family
from app.models.food_catalog import (
    FoodCompositionSnapshot,
    FoodItem,
    FoodNutrientComponent,
)
from app.models.nutrition_constraint import NutritionConstraint
from app.models.nutrition_plan import NutritionPlan, NutritionPlanRule
from app.models.person import Person

PLANNING_DATE = date(2026, 9, 16)
SCHEDULED_AT = datetime(2026, 9, 16, 12, 0, tzinfo=UTC)


def _override_db(db_session: Session):
    def override_get_db():
        yield db_session

    return override_get_db


def test_shared_recommendation_applies_each_persons_own_nutrition_plan(
    db_session: Session,
) -> None:
    family = Family(name="Shared Plan-Fit family", timezone="Europe/Lisbon")
    ana = Person(
        family=family,
        first_name="Ana",
        preferred_locale="pt-PT",
        timezone="Europe/Lisbon",
    )
    bruno = Person(
        family=family,
        first_name="Bruno",
        preferred_locale="pt-PT",
        timezone="Europe/Lisbon",
    )
    food = FoodItem(
        family=family,
        catalog_key="food:shared-plan-fit",
        name="Shared low protein lunch",
        food_kind="dish",
        suitable_meal_types=["lunch"],
        source="test",
    )
    composition = FoodCompositionSnapshot(
        food_item=food,
        reference_quantity=Decimal("100.0000"),
        reference_unit="g",
        energy_kcal=Decimal("350.0000"),
        data_version="shared-plan-fit-v1",
        source="test",
        effective_at=SCHEDULED_AT - timedelta(hours=1),
        nutrients=[
            FoodNutrientComponent(
                nutrient_key="protein",
                value=Decimal("10.0000"),
                unit="g",
            )
        ],
    )
    db_session.add_all([family, composition])
    db_session.flush()

    for person in (ana, bruno):
        db_session.add(
            DailyNutritionState(
                person=person,
                state_date=PLANNING_DATE,
                timezone="Europe/Lisbon",
                energy_consumed_kcal=Decimal("900.00"),
                energy_planned_kcal=Decimal("0.00"),
                energy_remaining_min_kcal=Decimal("300.00"),
                energy_remaining_max_kcal=Decimal("700.00"),
                calculation_version="shared-plan-fit-test-v1",
                computed_at=SCHEDULED_AT - timedelta(minutes=30),
            )
        )

    protein_rule = NutritionConstraint(
        person=bruno,
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
        person=bruno,
        lineage_id=uuid.uuid4(),
        version=1,
        title="Bruno lunch protein plan",
        source_type="nutritionist",
        source_name="Test nutritionist",
        status="active",
        valid_from=PLANNING_DATE,
        rules=[
            NutritionPlanRule(
                rule_kind="constraint",
                nutrition_constraint=protein_rule,
                meal_type="lunch",
                priority=120,
                source_statement="Lunch protein at least 15 g.",
                applies_outside_plan=False,
            )
        ],
    )
    db_session.add(plan)
    db_session.flush()

    assert family.id is not None
    assert ana.id is not None
    assert bruno.id is not None
    assert composition.id is not None
    payload = {
        "person_ids": [str(ana.id), str(bruno.id)],
        "planning_date": PLANNING_DATE.isoformat(),
        "scheduled_at": SCHEDULED_AT.isoformat(),
        "meal_type": "lunch",
        "candidates": [
            {
                "candidate_kind": "food_item",
                "composition_id": str(composition.id),
                "quantity": "100.0000",
                "quantity_unit": "g",
            }
        ],
        "location": None,
        "available_minutes": None,
        "has_kitchen": True,
        "source_kinds": ["home"],
    }

    app.dependency_overrides[get_db] = _override_db(db_session)
    try:
        with TestClient(app) as client:
            response = client.post(
                f"/api/families/{family.id}/meal-recommendations/shared-practical",
                json=payload,
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    body = response.json()
    assert body["engine_version"] == "shared-family-practical-plan-fit-v1+diversity-v1"
    option = body["options"][0]
    assert option["eligible"] is False
    assert option["rank"] is None
    assert (
        f"person:{bruno.id}:plan_fit_rule:meal:nutrient:protein:fail"
        in option["exclusion_reasons"]
    )
    assert f"person:{bruno.id}:plan_fit_status:fail" in option["exclusion_reasons"]
    assert not any(str(ana.id) in reason for reason in option["exclusion_reasons"])
