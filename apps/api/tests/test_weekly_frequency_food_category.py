from datetime import date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.models.family import Family
from app.models.food_catalog import FoodItem
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
from app.services.weekly_frequency_progress import get_weekly_frequency_progress

LISBON = ZoneInfo("Europe/Lisbon")


def test_weekly_progress_evaluates_imported_food_category_target(
    db_session: Session,
) -> None:
    family = Family(name="Food Category Family", timezone="Europe/Lisbon")
    person = Person(
        family=family,
        first_name="Ana",
        preferred_locale="pt-PT",
        timezone="Europe/Lisbon",
    )
    fish = FoodItem(
        family=family,
        catalog_key="dish:fish-category",
        name="Fish plate",
        food_kind="dish",
        source="test",
        is_active=True,
    )
    db_session.add_all([family, person, fish])
    db_session.flush()
    db_session.add(
        MealCandidatePlanningProfile(
            family_id=family.id,
            food_item_id=fish.id,
            candidate_kind="food_item",
            planning_category="main",
            primary_protein="fish",
            auto_plan_enabled=True,
            source="test",
        )
    )

    plan = create_nutrition_plan(
        db_session,
        person=person,
        data=NutritionPlanCreate(
            title="Imported weekly guidance",
            source_type="nutritionist",
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
            description="Fish at least twice per week",
            period="week",
            minimum_occurrences=2,
            is_mandatory=True,
        ),
    )
    update_nutrition_plan(
        db_session,
        plan=plan,
        data=NutritionPlanUpdate(status="active"),
    )

    for day in (14, 16):
        event = MealEvent(
            family_id=family.id,
            meal_type="lunch",
            scheduled_at=datetime(2026, 9, day, 13, 0, tzinfo=LISBON),
            timezone="Europe/Lisbon",
            status="completed",
            source="test",
        )
        participant = MealParticipant(
            meal_event=event,
            person_id=person.id,
            status="consumed",
        )
        participant.servings.append(
            Serving(
                food_item_id=fish.id,
                item_type="dish",
                item_key=fish.catalog_key,
                item_name=fish.name,
                status="consumed",
                nutrition_source="estimated",
            )
        )
        db_session.add(event)
    db_session.commit()

    result = get_weekly_frequency_progress(
        db_session,
        person_id=person.id,
        anchor_date=date(2026, 9, 16),
    )

    assert len(result.guidelines) == 1
    progress = result.guidelines[0]
    assert progress.target_type == "food_category"
    assert progress.evidence_status == "evaluated"
    assert progress.completed_occurrences == 2
    assert progress.total_occurrences == 2
    assert progress.remaining_minimum == 0
    assert progress.state == "achieved"
    assert all("primary_protein" in occurrence.matched_by for occurrence in progress.occurrences)
