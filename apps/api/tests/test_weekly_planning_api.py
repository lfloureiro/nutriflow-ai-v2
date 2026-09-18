from datetime import UTC, date, datetime
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.demo_seed import (
    DEMO_FAMILY_ID,
    DEMO_MARTA_ID,
    DEMO_PERSON_ID,
    seed_demo_dataset,
)
from app.development_breakfast_seed import seed_development_breakfast_catalog
from app.development_plan_fit_seed import seed_development_plan_fit
from app.development_transformation_seed import seed_development_transformations
from app.main import app
from app.models.daily_nutrition_state import DailyNutritionState
from app.models.family import Family
from app.models.food_catalog import Recipe, RecipeCompositionSnapshot
from app.models.meal import MealEvent
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
LUNCH_AT = datetime(2026, 9, 17, 12, 0, tzinfo=UTC)
DINNER_AT = datetime(2026, 9, 17, 19, 0, tzinfo=UTC)


def _override_db(db_session: Session):
    def override_get_db():
        yield db_session

    return override_get_db


def _setup(db_session: Session, key: str):
    family = Family(name=f"Weekly proposal {key}", timezone="Europe/Lisbon")
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
        recipe_key=f"family:weekly:{key}",
        name="Prato semanal",
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
        computed_at=LUNCH_AT,
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
                energy_remaining_max_kcal=Decimal(800),
                calculation_version=f"weekly-proposal-{key}",
                computed_at=LUNCH_AT,
            )
        )
    db_session.flush()
    return family, ana, bruno, recipe, composition


def _candidate(composition: RecipeCompositionSnapshot) -> dict[str, str]:
    assert composition.id is not None
    return {
        "candidate_kind": "recipe",
        "composition_id": str(composition.id),
        "quantity": "1",
        "quantity_unit": "serving",
    }


def _slot(
    key: str,
    *,
    scheduled_at: datetime,
    meal_type: str,
    composition: RecipeCompositionSnapshot,
) -> dict[str, object]:
    return {
        "slot_key": key,
        "planning_date": PLANNING_DATE.isoformat(),
        "scheduled_at": scheduled_at.isoformat(),
        "meal_type": meal_type,
        "candidates": [_candidate(composition)],
        "has_kitchen": True,
        "source_kinds": ["home"],
    }


def _post(
    db_session: Session,
    family: Family,
    *,
    ana: Person,
    bruno: Person,
    slots: list[dict[str, object]],
):
    assert family.id is not None
    assert ana.id is not None
    assert bruno.id is not None
    payload = {
        "person_ids": [str(ana.id), str(bruno.id)],
        "slots": slots,
        "max_combinations": 100,
    }
    app.dependency_overrides[get_db] = _override_db(db_session)
    try:
        with TestClient(app) as client:
            return client.post(
                f"/api/families/{family.id}/weekly-planning/proposals",
                json=payload,
            )
    finally:
        app.dependency_overrides.clear()


def _activate_recipe_maximum(
    db_session: Session,
    *,
    person: Person,
    recipe: Recipe,
    maximum: int,
) -> None:
    plan = create_nutrition_plan(
        db_session,
        person=person,
        data=NutritionPlanCreate(
            title="Weekly recipe maximum",
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
            target_type="recipe",
            target_key=recipe.recipe_key,
            description="Recipe weekly maximum",
            period="week",
            maximum_occurrences=maximum,
            is_mandatory=True,
            priority=120,
        ),
    )
    update_nutrition_plan(
        db_session,
        plan=plan,
        data=NutritionPlanUpdate(status="active"),
    )


def test_weekly_proposal_returns_selected_shared_plan_without_meal_events(
    db_session: Session,
) -> None:
    family, ana, bruno, recipe, composition = _setup(db_session, "selected")

    response = _post(
        db_session,
        family,
        ana=ana,
        bruno=bruno,
        slots=[
            _slot(
                "thu-lunch",
                scheduled_at=LUNCH_AT,
                meal_type="lunch",
                composition=composition,
            )
        ],
    )

    assert response.status_code == 201
    body = response.json()
    assert body["engine_version"] == "shared-weekly-multi-slot-v1"
    assert body["week_start"] == "2026-09-14"
    assert body["week_end"] == "2026-09-20"
    assert body["evaluated_combinations"] == 1
    assert body["feasible_combinations"] == 1
    assert body["selected_plan"] is not None, body
    choice = body["selected_plan"]["choices"][0]
    assert choice["slot_key"] == "thu-lunch"
    assert choice["candidate_key"] == recipe.recipe_key
    assert {participant["person_id"] for participant in choice["participants"]} == {
        str(ana.id),
        str(bruno.id),
    }
    assert "thu-lunch" in body["slot_engine_versions"]

    meal_count = db_session.scalar(select(func.count()).select_from(MealEvent))
    assert meal_count == 0


def test_weekly_proposal_rechecks_one_person_weekly_maximum_across_slots(
    db_session: Session,
) -> None:
    family, ana, bruno, recipe, composition = _setup(db_session, "maximum")
    _activate_recipe_maximum(
        db_session,
        person=ana,
        recipe=recipe,
        maximum=1,
    )
    db_session.commit()

    response = _post(
        db_session,
        family,
        ana=ana,
        bruno=bruno,
        slots=[
            _slot(
                "thu-lunch",
                scheduled_at=LUNCH_AT,
                meal_type="lunch",
                composition=composition,
            ),
            _slot(
                "thu-dinner",
                scheduled_at=DINNER_AT,
                meal_type="dinner",
                composition=composition,
            ),
        ],
    )

    assert response.status_code == 201
    body = response.json()
    assert body["selected_plan"] is None
    assert body["evaluated_combinations"] == 1
    assert body["feasible_combinations"] == 0
    assert body["rejected_by_person_weekly_maximum"] == 1
    assert body["rejected_by_person_daily_limit"] == 0


def test_weekly_proposal_rejects_duplicate_slot_keys_before_planning(
    db_session: Session,
) -> None:
    family, ana, bruno, _, composition = _setup(db_session, "duplicate")
    slot = _slot(
        "duplicate-slot",
        scheduled_at=LUNCH_AT,
        meal_type="lunch",
        composition=composition,
    )

    response = _post(
        db_session,
        family,
        ana=ana,
        bruno=bruno,
        slots=[slot, dict(slot)],
    )

    assert response.status_code == 422
    assert "slot keys must be unique" in response.json()["detail"]



def test_weekly_proposal_can_select_plan_adapted_variant_when_base_is_ineligible(
    db_session: Session,
) -> None:
    demo = seed_demo_dataset(
        db_session,
        now=datetime(2026, 9, 15, 12, 0, tzinfo=UTC),
    )
    family = db_session.get(Family, DEMO_FAMILY_ID)
    assert family is not None
    seed_development_breakfast_catalog(db_session, families=(family,))
    seed_development_transformations(db_session, families=(family,))
    seed_development_plan_fit(db_session, person_id=DEMO_PERSON_ID)
    db_session.commit()

    recipe = db_session.scalar(
        select(Recipe).where(
            Recipe.recipe_key == "breakfast:recipe:yogurt-muesli-banana"
        )
    )
    assert recipe is not None
    composition = db_session.scalar(
        select(RecipeCompositionSnapshot)
        .where(RecipeCompositionSnapshot.recipe_id == recipe.id)
        .order_by(RecipeCompositionSnapshot.computed_at.desc())
    )
    assert composition is not None
    assert composition.id is not None

    payload = {
        "person_ids": [str(DEMO_PERSON_ID), str(DEMO_MARTA_ID)],
        "slots": [
            {
                "slot_key": "tue-breakfast",
                "planning_date": demo.planning_date.isoformat(),
                "scheduled_at": "2026-09-15T08:30:00Z",
                "meal_type": "breakfast",
                "candidates": [
                    {
                        "candidate_kind": "recipe",
                        "composition_id": str(composition.id),
                        "quantity": "1",
                        "quantity_unit": "serving",
                    }
                ],
                "has_kitchen": True,
                "source_kinds": ["home"],
            }
        ],
        "max_combinations": 100,
    }

    app.dependency_overrides[get_db] = _override_db(db_session)
    try:
        with TestClient(app) as client:
            response = client.post(
                f"/api/families/{DEMO_FAMILY_ID}/weekly-planning/proposals",
                json=payload,
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    body = response.json()
    assert body["search_space_size"] > 0, body
    assert body["selected_plan"] is not None, body
    choice = body["selected_plan"]["choices"][0]
    assert choice["candidate_key"] == recipe.recipe_key
    assert choice["transformation"] is not None
    assert choice["transformation"]["kind"] == "plan_adapted"
    assert (
        choice["transformation"]["operation"]["replacement_food_name"]
        == "Iogurte grego"
    )
    assert choice["transformation"]["plan_improvement_participants"] == 1
    assert "weekly-transformations-v1" in body["slot_engine_versions"]["tue-breakfast"]

    primary = next(
        item
        for item in choice["participants"]
        if item["person_id"] == str(DEMO_PERSON_ID)
    )
    assert primary["score"] is not None
