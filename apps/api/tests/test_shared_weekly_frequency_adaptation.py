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
SCHEDULED_AT = datetime(2026, 9, 17, 12, 0, tzinfo=UTC)


def _override_db(db_session: Session):
    def override_get_db():
        yield db_session

    return override_get_db


def _food(
    db_session: Session,
    *,
    family: Family,
    key: str,
    name: str,
    primary_protein: str,
) -> FoodCompositionSnapshot:
    food = FoodItem(
        family=family,
        catalog_key=key,
        name=name,
        food_kind="dish",
        source="test",
        suitable_meal_types=["lunch"],
        is_active=True,
    )
    composition = FoodCompositionSnapshot(
        food_item=food,
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
    db_session.add(
        MealCandidatePlanningProfile(
            family_id=family.id,
            food_item_id=food.id,
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


def _candidate(composition: FoodCompositionSnapshot) -> dict[str, str]:
    assert composition.id is not None
    return {
        "candidate_kind": "food_item",
        "composition_id": str(composition.id),
        "quantity": "100.0000",
        "quantity_unit": "g",
    }


def test_shared_ranking_uses_person_specific_weekly_support(
    db_session: Session,
) -> None:
    family = Family(name="Shared weekly family", timezone="Europe/Lisbon")
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
    db_session.add(family)
    db_session.flush()

    fish = _food(
        db_session,
        family=family,
        key="dish:shared-fish",
        name="Shared fish lunch",
        primary_protein="fish",
    )
    beef = _food(
        db_session,
        family=family,
        key="dish:shared-beef",
        name="Shared beef lunch",
        primary_protein="red_meat",
    )

    for person in (ana, bruno):
        db_session.add(
            DailyNutritionState(
                person=person,
                state_date=PLANNING_DATE,
                timezone="Europe/Lisbon",
                energy_consumed_kcal=Decimal("0.00"),
                energy_planned_kcal=Decimal("0.00"),
                calculation_version="shared-weekly-test-v1",
                computed_at=SCHEDULED_AT,
            )
        )

    plan = create_nutrition_plan(
        db_session,
        person=ana,
        data=NutritionPlanCreate(
            title="Ana weekly fish guidance",
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
            target_key="fish",
            description="Fish at least three times per week",
            period="week",
            minimum_occurrences=3,
            is_mandatory=True,
            priority=120,
        ),
    )
    update_nutrition_plan(
        db_session,
        plan=plan,
        data=NutritionPlanUpdate(status="active"),
    )
    bruno.food_preferences.append(
        FoodPreference(
            subject_type="food",
            subject_key="dish:shared-beef",
            preference_type="like",
            intensity=5,
            source="user",
        )
    )
    db_session.commit()

    assert family.id is not None
    assert ana.id is not None
    assert bruno.id is not None
    payload = {
        "person_ids": [str(ana.id), str(bruno.id)],
        "planning_date": PLANNING_DATE.isoformat(),
        "scheduled_at": SCHEDULED_AT.isoformat(),
        "meal_type": "lunch",
        "candidates": [_candidate(beef), _candidate(fish)],
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
    assert "+shared-weekly-frequency-v1" in body["engine_version"]
    assert [option["candidate_key"] for option in body["options"]] == [
        "dish:shared-fish",
        "dish:shared-beef",
    ]
    fish_option = body["options"][0]
    assert fish_option["eligible"] is True
    ana_result = next(
        participant
        for participant in fish_option["participants"]
        if participant["person_id"] == str(ana.id)
    )
    assert "weekly_frequency_support:mandatory:1" in ana_result["explanation"]
