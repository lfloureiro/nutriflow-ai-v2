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
from app.models.meal import MealEvent, Serving
from app.models.meal_transformation_application import MealTransformationApplication
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


def _payload(
    *,
    ana: Person,
    bruno: Person,
    slots: list[dict[str, object]],
) -> dict[str, object]:
    assert ana.id is not None
    assert bruno.id is not None
    return {
        "person_ids": [str(ana.id), str(bruno.id)],
        "slots": slots,
        "max_combinations": 100,
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
    payload = _payload(ana=ana, bruno=bruno, slots=slots)
    app.dependency_overrides[get_db] = _override_db(db_session)
    try:
        with TestClient(app) as client:
            return client.post(
                f"/api/families/{family.id}/weekly-planning/proposals",
                json=payload,
            )
    finally:
        app.dependency_overrides.clear()


def _accept(
    db_session: Session,
    family: Family,
    *,
    proposal_payload: dict[str, object],
    slot_key: str,
    expected_candidate_key: str,
    expected_recipe_ingredient_id: str | None = None,
    expected_replacement_food_item_id: str | None = None,
):
    assert family.id is not None
    body: dict[str, object] = {
        "proposal": proposal_payload,
        "slot_key": slot_key,
        "expected_candidate_key": expected_candidate_key,
    }
    if expected_recipe_ingredient_id is not None:
        body["expected_recipe_ingredient_id"] = expected_recipe_ingredient_id
        body["expected_replacement_food_item_id"] = expected_replacement_food_item_id

    app.dependency_overrides[get_db] = _override_db(db_session)
    try:
        with TestClient(app) as client:
            return client.post(
                f"/api/families/{family.id}/weekly-planning/proposals/accept-slot",
                json=body,
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
    assert body["selected_plan"] is not None
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


def test_accept_weekly_proposal_slot_revalidates_and_materializes_base_recipe(
    db_session: Session,
) -> None:
    family, ana, bruno, recipe, composition = _setup(db_session, "accept")
    slot = _slot(
        "thu-lunch",
        scheduled_at=LUNCH_AT,
        meal_type="lunch",
        composition=composition,
    )
    proposal_payload = _payload(ana=ana, bruno=bruno, slots=[slot])

    response = _accept(
        db_session,
        family,
        proposal_payload=proposal_payload,
        slot_key="thu-lunch",
        expected_candidate_key=recipe.recipe_key,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["candidate_key"] == recipe.recipe_key
    assert body["status"] == "planned"
    assert body["transformation_application_id"] is None

    event = db_session.get(MealEvent, body["meal_event_id"])
    assert event is not None
    assert event.meal_type == "lunch"
    assert event.status == "planned"


def test_accept_weekly_proposal_slot_rejects_stale_candidate_without_persisting(
    db_session: Session,
) -> None:
    family, ana, bruno, _, composition = _setup(db_session, "stale")
    slot = _slot(
        "thu-lunch",
        scheduled_at=LUNCH_AT,
        meal_type="lunch",
        composition=composition,
    )

    response = _accept(
        db_session,
        family,
        proposal_payload=_payload(ana=ana, bruno=bruno, slots=[slot]),
        slot_key="thu-lunch",
        expected_candidate_key="recipe:not-the-selected-one",
    )

    assert response.status_code == 409
    assert "proposal changed" in response.json()["detail"]
    assert db_session.scalar(select(func.count()).select_from(MealEvent)) == 0


def _cancel_demo_breakfast(db_session: Session) -> None:
    event = db_session.scalar(
        select(MealEvent).where(
            MealEvent.family_id == DEMO_FAMILY_ID,
            MealEvent.meal_type == "breakfast",
        )
    )
    assert event is not None
    event.status = "cancelled"
    db_session.commit()


def _demo_transformation_payload(
    db_session: Session,
) -> tuple[Family, Recipe, dict[str, object]]:
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

    payload: dict[str, object] = {
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
    return family, recipe, payload


def _proposal_for_payload(
    db_session: Session,
    family: Family,
    payload: dict[str, object],
):
    app.dependency_overrides[get_db] = _override_db(db_session)
    try:
        with TestClient(app) as client:
            return client.post(
                f"/api/families/{family.id}/weekly-planning/proposals",
                json=payload,
            )
    finally:
        app.dependency_overrides.clear()


def test_accept_weekly_transformation_materializes_exact_reviewed_variant(
    db_session: Session,
) -> None:
    family, recipe, payload = _demo_transformation_payload(db_session)
    preview = _proposal_for_payload(db_session, family, payload)
    assert preview.status_code == 201
    choice = preview.json()["selected_plan"]["choices"][0]
    transformation = choice["transformation"]
    assert transformation is not None
    operation = transformation["operation"]

    _cancel_demo_breakfast(db_session)
    response = _accept(
        db_session,
        family,
        proposal_payload=payload,
        slot_key="tue-breakfast",
        expected_candidate_key=recipe.recipe_key,
        expected_recipe_ingredient_id=operation["recipe_ingredient_id"],
        expected_replacement_food_item_id=operation["replacement_food_item_id"],
    )

    assert response.status_code == 201
    body = response.json()
    assert body["candidate_key"] == recipe.recipe_key
    assert body["status"] == "planned"
    assert body["transformation_application_id"] is not None

    application = db_session.get(
        MealTransformationApplication,
        body["transformation_application_id"],
    )
    assert application is not None
    assert str(application.meal_event_id) == body["meal_event_id"]
    assert application.transformation_kind == "plan_adapted"
    assert application.replacement_food_name == "Iogurte grego"

    servings = list(
        db_session.scalars(
            select(Serving).where(
                Serving.meal_participant.has(meal_event_id=body["meal_event_id"])
            )
        ).all()
    )
    assert len(servings) == 2
    assert all(serving.nutrition_source == "transformed" for serving in servings)


def test_accept_weekly_transformation_rejects_stale_variant_identity(
    db_session: Session,
) -> None:
    family, recipe, payload = _demo_transformation_payload(db_session)
    preview = _proposal_for_payload(db_session, family, payload)
    assert preview.status_code == 201
    choice = preview.json()["selected_plan"]["choices"][0]
    transformation = choice["transformation"]
    assert transformation is not None
    operation = transformation["operation"]

    response = _accept(
        db_session,
        family,
        proposal_payload=payload,
        slot_key="tue-breakfast",
        expected_candidate_key=recipe.recipe_key,
        expected_recipe_ingredient_id=operation["recipe_ingredient_id"],
        expected_replacement_food_item_id="00000000-0000-4000-8000-000000000001",
    )

    assert response.status_code == 409
    assert "adaptation changed" in response.json()["detail"]
    assert (
        db_session.scalar(
            select(func.count()).select_from(MealTransformationApplication)
        )
        == 0
    )


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
    assert body["selected_plan"] is not None
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

