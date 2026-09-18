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


def _setup_family(
    db_session: Session,
    *,
    fish_key: str = "dish:shared-fish",
    beef_key: str = "dish:shared-beef",
) -> tuple[
    Family,
    Person,
    Person,
    FoodCompositionSnapshot,
    FoodCompositionSnapshot,
]:
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
        key=fish_key,
        name="Shared fish lunch",
        primary_protein="fish",
    )
    beef = _food(
        db_session,
        family=family,
        key=beef_key,
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
    db_session.flush()
    return family, ana, bruno, fish, beef


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
            title=f"{person.first_name} weekly {target_key} guidance",
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


def _activate_qualitative_guideline(
    db_session: Session,
    *,
    person: Person,
    target_key: str,
    mandatory: bool = True,
) -> None:
    plan = create_nutrition_plan(
        db_session,
        person=person,
        data=NutritionPlanCreate(
            title=f"{person.first_name} qualitative {target_key} guidance",
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
            target_key=target_key,
            description=f"Mandatory qualitative guidance for {target_key}",
            is_mandatory=mandatory,
            priority=120,
        ),
    )
    update_nutrition_plan(
        db_session,
        plan=plan,
        data=NutritionPlanUpdate(status="active"),
    )


def _recommend(
    db_session: Session,
    *,
    family: Family,
    ana: Person,
    bruno: Person,
    candidates: list[FoodCompositionSnapshot],
) -> dict[str, object]:
    assert family.id is not None
    assert ana.id is not None
    assert bruno.id is not None
    payload = {
        "person_ids": [str(ana.id), str(bruno.id)],
        "planning_date": PLANNING_DATE.isoformat(),
        "scheduled_at": SCHEDULED_AT.isoformat(),
        "meal_type": "lunch",
        "candidates": [_candidate(candidate) for candidate in candidates],
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
    return response.json()


def _participant(option: dict[str, object], person: Person) -> dict[str, object]:
    assert person.id is not None
    participants = option["participants"]
    assert isinstance(participants, list)
    return next(
        participant
        for participant in participants
        if participant["person_id"] == str(person.id)
    )


def test_shared_ranking_uses_person_specific_weekly_support(
    db_session: Session,
) -> None:
    family, ana, bruno, fish, beef = _setup_family(db_session)
    _activate_frequency_guideline(
        db_session,
        person=ana,
        target_key="fish",
        minimum=3,
        mandatory=True,
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

    body = _recommend(
        db_session,
        family=family,
        ana=ana,
        bruno=bruno,
        candidates=[beef, fish],
    )

    assert "+shared-weekly-frequency-v1" in body["engine_version"]
    options = body["options"]
    assert isinstance(options, list)
    assert [option["candidate_key"] for option in options] == [
        "dish:shared-fish",
        "dish:shared-beef",
    ]
    fish_option = options[0]
    assert fish_option["eligible"] is True
    ana_result = _participant(fish_option, ana)
    bruno_result = _participant(fish_option, bruno)
    assert "weekly_frequency_support:mandatory:1" in ana_result["explanation"]
    assert not any(
        marker.startswith("weekly_frequency_support:")
        for marker in bruno_result["explanation"]
    )


def test_shared_ranking_distinguishes_advisory_weekly_support(
    db_session: Session,
) -> None:
    family, ana, bruno, fish, beef = _setup_family(db_session)
    _activate_frequency_guideline(
        db_session,
        person=ana,
        target_key="fish",
        minimum=3,
        mandatory=False,
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

    body = _recommend(
        db_session,
        family=family,
        ana=ana,
        bruno=bruno,
        candidates=[beef, fish],
    )

    options = body["options"]
    assert isinstance(options, list)
    assert [option["candidate_key"] for option in options] == [
        "dish:shared-fish",
        "dish:shared-beef",
    ]
    ana_result = _participant(options[0], ana)
    assert "weekly_frequency_support:advisory:1" in ana_result["explanation"]


def test_mandatory_qualitative_guidance_does_not_make_all_shared_candidates_ineligible(
    db_session: Session,
) -> None:
    family, ana, bruno, fish, beef = _setup_family(db_session)
    _activate_qualitative_guideline(
        db_session,
        person=ana,
        target_key="refined_cereals",
        mandatory=True,
    )
    db_session.commit()

    body = _recommend(
        db_session,
        family=family,
        ana=ana,
        bruno=bruno,
        candidates=[fish, beef],
    )

    options = body["options"]
    assert isinstance(options, list)
    assert all(option["eligible"] is True for option in options)
    ana_result = _participant(options[0], ana)
    assert ana_result["plan_fit"]["status"] == "unknown"
    assert ana_result["plan_fit"]["nutrition_plan_authority"]["state"] == "partial_plan_coverage"


def test_weekly_support_never_rescues_another_participants_hard_failure(
    db_session: Session,
) -> None:
    family, ana, bruno, fish, beef = _setup_family(db_session)
    _activate_frequency_guideline(
        db_session,
        person=ana,
        target_key="fish",
        minimum=3,
        mandatory=True,
    )
    _activate_frequency_guideline(
        db_session,
        person=bruno,
        target_key="fish",
        maximum=0,
        mandatory=True,
    )
    db_session.commit()

    body = _recommend(
        db_session,
        family=family,
        ana=ana,
        bruno=bruno,
        candidates=[fish, beef],
    )

    options = body["options"]
    assert isinstance(options, list)
    by_key = {option["candidate_key"]: option for option in options}
    fish_option = by_key["dish:shared-fish"]
    assert fish_option["eligible"] is False
    assert fish_option["rank"] is None
    assert bruno.id is not None
    assert (
        f"person:{bruno.id}:plan_fit_guideline:frequency:food_category:fish:fail"
        in fish_option["exclusion_reasons"]
    )
    ana_result = _participant(fish_option, ana)
    assert "weekly_frequency_support:mandatory:1" in ana_result["explanation"]
    assert by_key["dish:shared-beef"]["eligible"] is True
    assert by_key["dish:shared-beef"]["rank"] == 1


def test_equal_weekly_support_preserves_existing_family_fairness(
    db_session: Session,
) -> None:
    family, ana, bruno, fish, beef = _setup_family(
        db_session,
        fish_key="dish:a-polarizing-fish",
        beef_key="dish:z-balanced-beef",
    )
    _activate_frequency_guideline(
        db_session,
        person=ana,
        target_key="fish",
        minimum=3,
        mandatory=True,
    )
    _activate_frequency_guideline(
        db_session,
        person=bruno,
        target_key="red_meat",
        minimum=3,
        mandatory=True,
    )
    ana.food_preferences.append(
        FoodPreference(
            subject_type="food",
            subject_key="dish:a-polarizing-fish",
            preference_type="like",
            intensity=5,
            source="user",
        )
    )
    bruno.food_preferences.append(
        FoodPreference(
            subject_type="food",
            subject_key="dish:a-polarizing-fish",
            preference_type="dislike",
            intensity=5,
            source="user",
        )
    )
    db_session.commit()

    body = _recommend(
        db_session,
        family=family,
        ana=ana,
        bruno=bruno,
        candidates=[fish, beef],
    )

    options = body["options"]
    assert isinstance(options, list)
    assert [option["candidate_key"] for option in options] == [
        "dish:z-balanced-beef",
        "dish:a-polarizing-fish",
    ]
    assert options[0]["minimum_score"] > options[1]["minimum_score"]
