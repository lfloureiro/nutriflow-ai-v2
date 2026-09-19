from datetime import UTC, date, datetime
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

import app.services.meal_plan_fit as meal_plan_fit_service
import app.services.meal_plan_fit_weekly_frequency as weekly_fit_service
import app.services.meal_recommendation_api as meal_recommendation_api_service
import app.services.planning_bootstrap_api as planning_bootstrap_service
import app.services.shared_meal_transformation as shared_transformation_service
import app.services.weekly_planning_api as weekly_planning_service
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
from app.models.food_catalog import (
    Recipe,
    RecipeCompositionSnapshot,
    RecipeNutrientComponent,
)
from app.models.meal import MealEvent, Serving
from app.models.meal_candidate_availability import MealCandidateAvailability
from app.models.meal_transformation_application import MealTransformationApplication
from app.models.nutrition_constraint import NutritionConstraint
from app.models.person import Person
from app.schemas.nutrition_plan import (
    NutritionPlanCreate,
    NutritionPlanGuidelineCreate,
    NutritionPlanRuleCreate,
    NutritionPlanUpdate,
)
from app.services.nutrition_plan import (
    add_nutrition_plan_guideline,
    add_nutrition_plan_rule,
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
    assert body["selected_plan"] is not None
    choice = body["selected_plan"]["choices"][0]
    assert choice["slot_key"] == "thu-lunch"
    assert choice["candidate_key"] == recipe.recipe_key
    assert choice["recipe_id"] == str(recipe.id)
    assert {participant["person_id"] for participant in choice["participants"]} == {
        str(ana.id),
        str(bruno.id),
    }
    for participant in choice["participants"]:
        assert participant["daily_nutrition_state_id"] is not None
        assert Decimal(participant["nutrition"]["energy_kcal"]) == Decimal(500)
        assert participant["nutrition"]["nutrients"] == {}
        assert participant["plan_rule_results"] == []
        assert participant["plan_guidance"] == []
    assert "thu-lunch" in body["slot_engine_versions"]

    meal_count = db_session.scalar(select(func.count()).select_from(MealEvent))
    assert meal_count == 0




def test_weekly_proposal_exposes_person_specific_nutrition_plan_authority(
    db_session: Session,
) -> None:
    family, ana, bruno, _, composition = _setup(db_session, "authority")

    plan = create_nutrition_plan(
        db_session,
        person=ana,
        data=NutritionPlanCreate(
            title="Plano da nutricionista",
            source_type="nutritionist",
            source_name="Dietitian",
            valid_from=date(2026, 9, 1),
        ),
    )
    add_nutrition_plan_guideline(
        db_session,
        plan=plan,
        data=NutritionPlanGuidelineCreate(
            guideline_type="qualitative",
            target_type="food_category",
            target_key="vegetables",
            description="Incluir vegetais.",
            is_mandatory=True,
            priority=120,
        ),
    )
    update_nutrition_plan(
        db_session,
        plan=plan,
        data=NutritionPlanUpdate(status="active"),
    )

    response = _post(
        db_session,
        family,
        ana=ana,
        bruno=bruno,
        slots=[
            _slot(
                "thu-lunch-authority",
                scheduled_at=LUNCH_AT,
                meal_type="lunch",
                composition=composition,
            )
        ],
    )

    assert response.status_code == 201
    body = response.json()
    assert body["selected_plan"] is not None
    participants = {
        item["person_id"]: item
        for item in body["selected_plan"]["choices"][0]["participants"]
    }

    assert ana.id is not None
    assert bruno.id is not None
    ana_read = participants[str(ana.id)]
    assert ana_read["nutrition_plan_authority"] == "partial_plan_coverage"
    assert ana_read["active_plan_ids"] == [str(plan.id)]
    assert ana_read["active_plan_titles"] == ["Plano da nutricionista"]
    assert ana_read["plan_fit_status"] == "unknown"
    assert ana_read["plan_fit_score"] is None
    assert ana_read["plan_unknown_evidence"]
    assert ana_read["plan_guidance"] == ["Incluir vegetais."]

    bruno_read = participants[str(bruno.id)]
    assert bruno_read["nutrition_plan_authority"] == "no_active_plan"
    assert bruno_read["active_plan_ids"] == []
    assert bruno_read["active_plan_titles"] == []


def test_weekly_proposal_exposes_plan_backed_nutrient_comparison(
    db_session: Session,
) -> None:
    family, ana, bruno, _, composition = _setup(db_session, "nutrient-comparison")
    composition.nutrients.append(
        RecipeNutrientComponent(
            nutrient_key="protein",
            value=Decimal(45),
            unit="g",
        )
    )
    db_session.flush()

    assert ana.id is not None
    constraint = NutritionConstraint(
        person_id=ana.id,
        constraint_type="nutrient_target",
        target_type="nutrient",
        target_key="protein",
        operator="range",
        value_min=Decimal(40),
        value_max=Decimal(50),
        unit="g",
        severity="required",
        is_mandatory=True,
        source="nutritionist",
        source_name="Dietitian",
    )
    db_session.add(constraint)
    db_session.flush()

    plan = create_nutrition_plan(
        db_session,
        person=ana,
        data=NutritionPlanCreate(
            title="Plano proteico",
            source_type="nutritionist",
            source_name="Dietitian",
            valid_from=date(2026, 9, 1),
        ),
    )
    add_nutrition_plan_rule(
        db_session,
        plan=plan,
        data=NutritionPlanRuleCreate(
            rule_kind="constraint",
            reference_id=constraint.id,
            meal_type="lunch",
            source_statement="40-50 g de proteína ao almoço.",
        ),
    )
    update_nutrition_plan(
        db_session,
        plan=plan,
        data=NutritionPlanUpdate(status="active"),
    )

    response = _post(
        db_session,
        family,
        ana=ana,
        bruno=bruno,
        slots=[
            _slot(
                "thu-lunch-nutrition",
                scheduled_at=LUNCH_AT,
                meal_type="lunch",
                composition=composition,
            )
        ],
    )

    assert response.status_code == 201
    body = response.json()
    assert body["selected_plan"] is not None
    choice = body["selected_plan"]["choices"][0]
    ana_read = next(
        item for item in choice["participants"] if item["person_id"] == str(ana.id)
    )

    assert Decimal(ana_read["nutrition"]["nutrients"]["protein"]["value"]) == Decimal(45)
    assert ana_read["nutrition"]["nutrients"]["protein"]["unit"] == "g"
    assert len(ana_read["plan_rule_results"]) == 1
    rule = ana_read["plan_rule_results"][0]
    assert rule["target_type"] == "nutrient"
    assert rule["target_key"] == "protein"
    assert rule["scope"] == "meal"
    assert rule["status"] == "pass"
    assert Decimal(rule["observed_value"]) == Decimal(45)
    assert Decimal(rule["target_min"]) == Decimal(40)
    assert Decimal(rule["target_max"]) == Decimal(50)
    assert rule["source"]["plan_id"] == str(plan.id)


def test_weekly_proposal_skips_unavailable_slot_but_plans_remaining_slots(
    db_session: Session,
) -> None:
    family, ana, bruno, _, composition = _setup(db_session, "partial-unavailable")
    assert family.id is not None

    unavailable_recipe = Recipe(
        family=family,
        recipe_key="family:weekly:partial-unavailable:delivery",
        name="Prato delivery indisponível",
        serving_count=Decimal(2),
        source="test",
    )
    unavailable_composition = RecipeCompositionSnapshot(
        recipe=unavailable_recipe,
        reference_quantity=Decimal(1),
        reference_unit="serving",
        energy_kcal=Decimal(500),
        composition_version="test-v1",
        calculation_version="test",
        computed_at=LUNCH_AT,
    )
    db_session.add(unavailable_composition)
    db_session.flush()
    assert unavailable_recipe.id is not None

    db_session.add(
        MealCandidateAvailability(
            family_id=family.id,
            recipe_id=unavailable_recipe.id,
            candidate_kind="recipe",
            source_kind="delivery",
            source_key="test:delivery:unavailable",
            requires_kitchen=False,
            is_available=False,
            source="test",
        )
    )
    db_session.flush()

    unavailable_lunch = _slot(
        "thu-lunch-unavailable",
        scheduled_at=LUNCH_AT,
        meal_type="lunch",
        composition=unavailable_composition,
    )
    unavailable_lunch["source_kinds"] = ["delivery"]
    unavailable_lunch["has_kitchen"] = False

    response = _post(
        db_session,
        family,
        ana=ana,
        bruno=bruno,
        slots=[
            unavailable_lunch,
            _slot(
                "thu-dinner-available",
                scheduled_at=DINNER_AT,
                meal_type="dinner",
                composition=composition,
            ),
        ],
    )

    assert response.status_code == 201
    body = response.json()
    assert body["selected_plan"] is not None
    assert [
        choice["slot_key"] for choice in body["selected_plan"]["choices"]
    ] == ["thu-dinner-available"]
    assert body["skipped_slots"] == [
        {
            "slot_key": "thu-lunch-unavailable",
            "planning_date": PLANNING_DATE.isoformat(),
            "meal_type": "lunch",
            "reason": "no_eligible_candidates",
            "exclusion_reasons": sorted(
                [
                    f"person:{ana.id}:candidate_unavailable",
                    f"person:{bruno.id}:candidate_unavailable",
                ]
            ),
        }
    ]
    assert body["search_space_size"] == 1
    assert body["feasible_combinations"] == 1


def test_weekly_proposal_skips_transformation_service_when_recipe_has_no_variants(
    db_session: Session,
    monkeypatch,
) -> None:
    family, ana, bruno, _, composition = _setup(db_session, "no-transform-variants")

    def unexpected_transformation(*args, **kwargs):
        raise AssertionError("Transformation service must not run without configured variants.")

    monkeypatch.setattr(
        weekly_planning_service,
        "propose_shared_meal_transformations",
        unexpected_transformation,
    )

    response = _post(
        db_session,
        family,
        ana=ana,
        bruno=bruno,
        slots=[
            _slot(
                "thu-lunch-no-transform",
                scheduled_at=LUNCH_AT,
                meal_type="lunch",
                composition=composition,
            )
        ],
    )

    assert response.status_code == 201
    assert response.json()["selected_plan"] is not None


def test_weekly_proposal_reuses_request_scoped_plan_context(
    db_session: Session,
    monkeypatch,
) -> None:
    family, ana, bruno, _, composition = _setup(db_session, "request-cache")

    calls = {
        "ensure_state": 0,
        "compile_effective": 0,
        "weekly_progress": 0,
        "candidate_catalogue_loads": 0,
    }
    friday_date = date(2026, 9, 18)
    friday_at = datetime(2026, 9, 18, 12, 0, tzinfo=UTC)
    for person in (ana, bruno):
        db_session.add(
            DailyNutritionState(
                person=person,
                state_date=friday_date,
                timezone="Europe/Lisbon",
                energy_consumed_kcal=Decimal(1000),
                energy_planned_kcal=Decimal(0),
                energy_remaining_min_kcal=Decimal(400),
                energy_remaining_max_kcal=Decimal(800),
                calculation_version="weekly-proposal-request-cache-friday",
                computed_at=friday_at,
            )
        )
    db_session.flush()

    def unexpected_plan_fit_candidate_reload(*args, **kwargs):
        raise AssertionError(
            "Weekly shared Plan-Fit must reuse candidates already loaded by the recommendation path."
        )

    monkeypatch.setattr(
        meal_plan_fit_service,
        "_load_candidates",
        unexpected_plan_fit_candidate_reload,
    )

    original_candidate_loader = meal_recommendation_api_service._load_candidates
    original_ensure_state = planning_bootstrap_service._ensure_daily_state
    original_base_compile = meal_plan_fit_service.compile_effective_nutrition_plan
    original_weekly_compile = weekly_fit_service.compile_effective_nutrition_plan
    original_weekly_progress = weekly_fit_service.get_weekly_frequency_progress

    def counted_candidate_loader(*args, **kwargs):
        calls["candidate_catalogue_loads"] += 1
        return original_candidate_loader(*args, **kwargs)

    def counted_ensure_state(*args, **kwargs):
        calls["ensure_state"] += 1
        return original_ensure_state(*args, **kwargs)

    def counted_base_compile(*args, **kwargs):
        calls["compile_effective"] += 1
        return original_base_compile(*args, **kwargs)

    def counted_weekly_compile(*args, **kwargs):
        calls["compile_effective"] += 1
        return original_weekly_compile(*args, **kwargs)

    def counted_weekly_progress(*args, **kwargs):
        calls["weekly_progress"] += 1
        return original_weekly_progress(*args, **kwargs)

    monkeypatch.setattr(
        meal_recommendation_api_service,
        "_load_candidates",
        counted_candidate_loader,
    )
    monkeypatch.setattr(
        planning_bootstrap_service,
        "_ensure_daily_state",
        counted_ensure_state,
    )
    monkeypatch.setattr(
        meal_plan_fit_service,
        "compile_effective_nutrition_plan",
        counted_base_compile,
    )
    monkeypatch.setattr(
        weekly_fit_service,
        "compile_effective_nutrition_plan",
        counted_weekly_compile,
    )
    monkeypatch.setattr(
        weekly_fit_service,
        "get_weekly_frequency_progress",
        counted_weekly_progress,
    )

    response = _post(
        db_session,
        family,
        ana=ana,
        bruno=bruno,
        slots=[
            _slot(
                "thu-lunch-cache",
                scheduled_at=LUNCH_AT,
                meal_type="lunch",
                composition=composition,
            ),
            _slot(
                "thu-dinner-cache",
                scheduled_at=DINNER_AT,
                meal_type="dinner",
                composition=composition,
            ),
            {
                **_slot(
                    "fri-lunch-cache",
                    scheduled_at=friday_at,
                    meal_type="lunch",
                    composition=composition,
                ),
                "planning_date": friday_date.isoformat(),
            },
        ],
    )

    assert response.status_code == 201
    assert calls["ensure_state"] == 4
    assert calls["compile_effective"] == 6
    assert calls["weekly_progress"] == 0
    assert calls["candidate_catalogue_loads"] == 3

def test_weekly_progress_is_loaded_once_per_guided_person_for_the_week(
    db_session: Session,
    monkeypatch,
) -> None:
    family, ana, bruno, recipe, composition = _setup(db_session, "weekly-progress-cache")
    _activate_recipe_maximum(
        db_session,
        person=ana,
        recipe=recipe,
        maximum=10,
    )

    friday_date = date(2026, 9, 18)
    friday_at = datetime(2026, 9, 18, 12, 0, tzinfo=UTC)
    for person in (ana, bruno):
        db_session.add(
            DailyNutritionState(
                person=person,
                state_date=friday_date,
                timezone="Europe/Lisbon",
                energy_consumed_kcal=Decimal(1000),
                energy_planned_kcal=Decimal(0),
                energy_remaining_min_kcal=Decimal(400),
                energy_remaining_max_kcal=Decimal(800),
                calculation_version="weekly-progress-cache-friday",
                computed_at=friday_at,
            )
        )
    db_session.commit()

    calls = 0
    original = weekly_fit_service.get_weekly_frequency_progress

    def counted_weekly_progress(*args, **kwargs):
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(
        weekly_fit_service,
        "get_weekly_frequency_progress",
        counted_weekly_progress,
    )

    friday_slot = _slot(
        "fri-lunch-weekly-cache",
        scheduled_at=friday_at,
        meal_type="lunch",
        composition=composition,
    )
    friday_slot["planning_date"] = friday_date.isoformat()

    response = _post(
        db_session,
        family,
        ana=ana,
        bruno=bruno,
        slots=[
            _slot(
                "thu-lunch-weekly-cache",
                scheduled_at=LUNCH_AT,
                meal_type="lunch",
                composition=composition,
            ),
            friday_slot,
        ],
    )

    assert response.status_code == 201
    assert response.json()["selected_plan"] is not None
    assert calls == 1


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
    monkeypatch,
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

    def unexpected_baseline_recompute(*args, **kwargs):
        raise AssertionError("Weekly transformation must reuse existing baseline Plan-Fit.")

    monkeypatch.setattr(
        shared_transformation_service,
        "evaluate_meal_plan_fit_with_weekly_frequency",
        unexpected_baseline_recompute,
    )

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




def _expected_choices_from_proposal(body: dict[str, object]) -> list[dict[str, str]]:
    selected = body["selected_plan"]
    assert isinstance(selected, dict)
    choices = selected["choices"]
    assert isinstance(choices, list)
    result: list[dict[str, str]] = []
    for raw_choice in choices:
        assert isinstance(raw_choice, dict)
        choice = {
            "slot_key": str(raw_choice["slot_key"]),
            "candidate_key": str(raw_choice["candidate_key"]),
        }
        transformation = raw_choice.get("transformation")
        if isinstance(transformation, dict):
            operation = transformation["operation"]
            assert isinstance(operation, dict)
            choice["recipe_ingredient_id"] = str(operation["recipe_ingredient_id"])
            choice["replacement_food_item_id"] = str(
                operation["replacement_food_item_id"]
            )
        result.append(choice)
    return result


def _plan_payload(
    *,
    person_ids: list[str],
    slots: list[dict[str, object]],
    proposal_body: dict[str, object],
) -> dict[str, object]:
    return {
        "person_ids": person_ids,
        "slots": slots,
        "max_combinations": 100,
        "expected_choices": _expected_choices_from_proposal(proposal_body),
    }


def test_weekly_plan_materializes_normal_shared_choice_atomically(
    db_session: Session,
) -> None:
    family, ana, bruno, recipe, composition = _setup(db_session, "materialize")
    assert family.id is not None
    assert ana.id is not None
    assert bruno.id is not None
    slots = [
        _slot(
            "thu-lunch",
            scheduled_at=LUNCH_AT,
            meal_type="lunch",
            composition=composition,
        )
    ]

    proposal = _post(
        db_session,
        family,
        ana=ana,
        bruno=bruno,
        slots=slots,
    )
    assert proposal.status_code == 201
    proposal_body = proposal.json()
    assert proposal_body["selected_plan"] is not None

    app.dependency_overrides[get_db] = _override_db(db_session)
    try:
        with TestClient(app) as client:
            response = client.post(
                f"/api/families/{family.id}/weekly-planning/plan",
                json=_plan_payload(
                    person_ids=[str(ana.id), str(bruno.id)],
                    slots=slots,
                    proposal_body=proposal_body,
                ),
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "planned"
    assert len(body["choices"]) == 1
    choice = body["choices"][0]
    assert choice["slot_key"] == "thu-lunch"
    assert choice["candidate_key"] == recipe.recipe_key
    assert choice["transformation_application_id"] is None
    assert len(choice["serving_ids"]) == 2

    event_count = db_session.scalar(select(func.count()).select_from(MealEvent))
    serving_count = db_session.scalar(select(func.count()).select_from(Serving))
    assert event_count == 1
    assert serving_count == 2


def test_weekly_plan_rejects_stale_selection_without_persisting(
    db_session: Session,
) -> None:
    family, ana, bruno, _, composition = _setup(db_session, "stale")
    assert family.id is not None
    assert ana.id is not None
    assert bruno.id is not None
    slots = [
        _slot(
            "thu-lunch",
            scheduled_at=LUNCH_AT,
            meal_type="lunch",
            composition=composition,
        )
    ]

    proposal = _post(
        db_session,
        family,
        ana=ana,
        bruno=bruno,
        slots=slots,
    )
    assert proposal.status_code == 201
    payload = _plan_payload(
        person_ids=[str(ana.id), str(bruno.id)],
        slots=slots,
        proposal_body=proposal.json(),
    )
    expected = payload["expected_choices"]
    assert isinstance(expected, list)
    assert isinstance(expected[0], dict)
    expected[0]["candidate_key"] = "stale:candidate"

    app.dependency_overrides[get_db] = _override_db(db_session)
    try:
        with TestClient(app) as client:
            response = client.post(
                f"/api/families/{family.id}/weekly-planning/plan",
                json=payload,
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 409
    assert "selection changed" in response.json()["detail"]
    event_count = db_session.scalar(select(func.count()).select_from(MealEvent))
    assert event_count == 0


def test_weekly_plan_rolls_back_earlier_slot_when_later_slot_conflicts(
    db_session: Session,
) -> None:
    family, ana, bruno, _, composition = _setup(db_session, "atomic-conflict")
    assert family.id is not None
    assert ana.id is not None
    assert bruno.id is not None
    slots = [
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
    ]

    proposal = _post(
        db_session,
        family,
        ana=ana,
        bruno=bruno,
        slots=slots,
    )
    assert proposal.status_code == 201
    proposal_body = proposal.json()
    assert proposal_body["selected_plan"] is not None

    conflict = MealEvent(
        family_id=family.id,
        meal_type="dinner",
        title="Existing dinner",
        scheduled_at=DINNER_AT,
        timezone=family.timezone,
        status="planned",
        source="manual",
    )
    db_session.add(conflict)
    db_session.commit()
    assert conflict.id is not None

    app.dependency_overrides[get_db] = _override_db(db_session)
    try:
        with TestClient(app) as client:
            response = client.post(
                f"/api/families/{family.id}/weekly-planning/plan",
                json=_plan_payload(
                    person_ids=[str(ana.id), str(bruno.id)],
                    slots=slots,
                    proposal_body=proposal_body,
                ),
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 409
    assert "already planned" in response.json()["detail"]
    events = list(
        db_session.scalars(
            select(MealEvent).where(MealEvent.family_id == family.id)
        ).all()
    )
    assert [event.id for event in events] == [conflict.id]


def test_weekly_plan_materializes_selected_transformation(
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

    seeded_breakfast = db_session.scalar(
        select(MealEvent).where(
            MealEvent.family_id == DEMO_FAMILY_ID,
            MealEvent.meal_type == "breakfast",
        )
    )
    assert seeded_breakfast is not None
    seeded_breakfast.status = "cancelled"
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

    slots = [
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
    ]
    proposal_payload = {
        "person_ids": [str(DEMO_PERSON_ID), str(DEMO_MARTA_ID)],
        "slots": slots,
        "max_combinations": 100,
    }

    app.dependency_overrides[get_db] = _override_db(db_session)
    try:
        with TestClient(app) as client:
            proposal = client.post(
                f"/api/families/{DEMO_FAMILY_ID}/weekly-planning/proposals",
                json=proposal_payload,
            )
            assert proposal.status_code == 201
            proposal_body = proposal.json()
            assert proposal_body["selected_plan"] is not None
            selected = proposal_body["selected_plan"]["choices"][0]
            assert selected["transformation"] is not None

            response = client.post(
                f"/api/families/{DEMO_FAMILY_ID}/weekly-planning/plan",
                json={
                    **proposal_payload,
                    "expected_choices": _expected_choices_from_proposal(
                        proposal_body
                    ),
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "planned"
    assert len(body["choices"]) == 1
    planned_choice = body["choices"][0]
    assert planned_choice["candidate_key"] == recipe.recipe_key
    assert planned_choice["transformation_application_id"] is not None
    assert len(planned_choice["serving_ids"]) == 2

    application = db_session.get(
        MealTransformationApplication,
        planned_choice["transformation_application_id"],
    )
    assert application is not None
    assert application.recipe_id == recipe.id
    assert application.transformation_kind == "plan_adapted"

    servings = list(
        db_session.scalars(
            select(Serving).where(
                Serving.id.in_(planned_choice["serving_ids"])
            )
        ).all()
    )
    assert len(servings) == 2
    assert all(serving.recipe_id == recipe.id for serving in servings)
    assert all(serving.nutrition_source == "transformed" for serving in servings)
