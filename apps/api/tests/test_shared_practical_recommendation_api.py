from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.main import app
from app.models.daily_nutrition_state import DailyNutritionState
from app.models.family import Family
from app.models.food_catalog import Recipe, RecipeCompositionSnapshot
from app.models.meal import MealEvent
from app.models.nutrition_constraint import NutritionConstraint
from app.models.person import Person

PLANNING_DATE = date(2026, 8, 22)
SCHEDULED_AT = datetime(2026, 8, 22, 12, 0, tzinfo=UTC)


def _override_db(db_session: Session):
    def override_get_db():
        yield db_session

    return override_get_db


def _base(db_session: Session, key: str):
    family = Family(name=f"Shared {key}", timezone="Europe/Lisbon")
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
    recipe = Recipe(
        family=family,
        recipe_key=f"family:shared:recipe:{key}",
        name="Massa partilhada",
        serving_count=Decimal(2),
        source="test",
    )
    composition = RecipeCompositionSnapshot(
        recipe=recipe,
        reference_quantity=Decimal(1),
        reference_unit="serving",
        energy_kcal=Decimal(500),
        composition_version="test-v1",
        calculation_version="test",
        computed_at=SCHEDULED_AT - timedelta(hours=1),
    )
    db_session.add_all([family, composition])
    db_session.flush()

    for person in (ana, bruno):
        db_session.add(
            DailyNutritionState(
                person=person,
                state_date=PLANNING_DATE,
                timezone="Europe/Lisbon",
                energy_consumed_kcal=Decimal(1000),
                energy_planned_kcal=Decimal(0),
                energy_remaining_min_kcal=Decimal(400),
                energy_remaining_max_kcal=Decimal(700),
                calculation_version=f"shared-api-{key}",
                computed_at=SCHEDULED_AT - timedelta(minutes=30),
            )
        )
    db_session.flush()
    return family, ana, bruno, recipe, composition


def _payload(ana: Person, bruno: Person, composition: RecipeCompositionSnapshot):
    assert ana.id is not None
    assert bruno.id is not None
    assert composition.id is not None
    return {
        "person_ids": [str(ana.id), str(bruno.id)],
        "planning_date": PLANNING_DATE.isoformat(),
        "scheduled_at": SCHEDULED_AT.isoformat(),
        "meal_type": "lunch",
        "candidates": [
            {
                "candidate_kind": "recipe",
                "composition_id": str(composition.id),
                "quantity": "1",
                "quantity_unit": "serving",
            }
        ],
        "location": None,
        "available_minutes": None,
        "has_kitchen": True,
        "source_kinds": ["home"],
    }


def _post(db_session: Session, family: Family, path: str, payload: dict[str, object]):
    app.dependency_overrides[get_db] = _override_db(db_session)
    try:
        with TestClient(app) as client:
            return client.post(f"/api/families/{family.id}{path}", json=payload)
    finally:
        app.dependency_overrides.clear()


def test_shared_practical_recommendation_returns_one_group_option(db_session: Session) -> None:
    family, ana, bruno, _, composition = _base(db_session, "recommend")

    response = _post(
        db_session,
        family,
        "/meal-recommendations/shared-practical",
        _payload(ana, bruno, composition),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["person_ids"] == [str(ana.id), str(bruno.id)]
    assert body["engine_version"] == "shared-family-practical-v1"
    assert len(body["options"]) == 1
    option = body["options"][0]
    assert option["eligible"] is True
    assert option["rank"] == 1
    assert {participant["person_id"] for participant in option["participants"]} == {
        str(ana.id),
        str(bruno.id),
    }


def test_shared_practical_recommendation_respects_one_person_mandatory_rule(
    db_session: Session,
) -> None:
    family, ana, bruno, recipe, composition = _base(db_session, "excluded")
    bruno.nutrition_constraints.append(
        NutritionConstraint(
            constraint_type="exclude",
            target_type="recipe",
            target_key=recipe.recipe_key,
            operator="exclude",
            severity="required",
            is_mandatory=True,
            source="test",
        )
    )
    db_session.flush()

    response = _post(
        db_session,
        family,
        "/meal-recommendations/shared-practical",
        _payload(ana, bruno, composition),
    )

    assert response.status_code == 201
    option = response.json()["options"][0]
    assert option["eligible"] is False
    assert any(str(bruno.id) in reason for reason in option["exclusion_reasons"])


def test_shared_practical_plan_creates_one_meal_event_with_two_people(
    db_session: Session,
) -> None:
    family, ana, bruno, recipe, composition = _base(db_session, "plan")
    payload = _payload(ana, bruno, composition)
    payload["candidate_key"] = recipe.recipe_key
    payload["title"] = recipe.name

    response = _post(
        db_session,
        family,
        "/meal-recommendations/shared-practical/plan",
        payload,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "planned"
    assert set(body["person_ids"]) == {str(ana.id), str(bruno.id)}
    assert len(body["serving_ids"]) == 2

    events = list(db_session.scalars(select(MealEvent).where(MealEvent.family_id == family.id)).all())
    assert len(events) == 1
    event = events[0]
    db_session.refresh(event, attribute_names=["participants"])
    assert len(event.participants) == 2
