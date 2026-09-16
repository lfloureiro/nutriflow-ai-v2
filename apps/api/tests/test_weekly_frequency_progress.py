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
UTC = ZoneInfo("UTC")


def _setup_people(db_session: Session) -> tuple[Family, Person, Person]:
    family = Family(name="Weekly Family", timezone="Europe/Lisbon")
    person = Person(
        family=family,
        first_name="Ana",
        preferred_locale="pt-PT",
        timezone="Europe/Lisbon",
    )
    other = Person(
        family=family,
        first_name="Bruno",
        preferred_locale="pt-PT",
        timezone="Europe/Lisbon",
    )
    db_session.add_all([family, person, other])
    db_session.flush()
    return family, person, other


def _food(
    db_session: Session,
    *,
    family: Family,
    key: str,
    name: str,
    protein: str | None,
) -> FoodItem:
    item = FoodItem(
        family_id=family.id,
        catalog_key=key,
        name=name,
        food_kind="dish",
        source="test",
        is_active=True,
    )
    db_session.add(item)
    db_session.flush()
    if protein is not None:
        db_session.add(
            MealCandidatePlanningProfile(
                family_id=family.id,
                food_item_id=item.id,
                recipe_id=None,
                candidate_kind="food_item",
                planning_category="main",
                primary_protein=protein,
                auto_plan_enabled=True,
                source="test",
            )
        )
        db_session.flush()
    return item


def _meal(
    db_session: Session,
    *,
    family: Family,
    person: Person,
    scheduled_at: datetime,
    food: FoodItem,
    event_status: str = "planned",
    participant_status: str = "planned",
    serving_status: str = "planned",
) -> MealEvent:
    event = MealEvent(
        family_id=family.id,
        meal_type="lunch",
        scheduled_at=scheduled_at,
        timezone="Europe/Lisbon",
        status=event_status,
        source="test",
    )
    participant = MealParticipant(
        meal_event=event,
        person_id=person.id,
        status=participant_status,
    )
    participant.servings.append(
        Serving(
            food_item_id=food.id,
            recipe_id=None,
            item_type="dish",
            item_key=food.catalog_key,
            item_name=food.name,
            status=serving_status,
            nutrition_source="estimated",
        )
    )
    db_session.add(event)
    db_session.flush()
    return event


def _activate_frequency_plan(db_session: Session, person: Person) -> None:
    plan = create_nutrition_plan(
        db_session,
        person=person,
        data=NutritionPlanCreate(
            title="Weekly guidance",
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
            target_type="food_group",
            target_key="fish",
            description="Fish at least three times per week",
            period="week",
            minimum_occurrences=3,
            is_mandatory=True,
        ),
    )
    add_nutrition_plan_guideline(
        db_session,
        plan=plan,
        data=NutritionPlanGuidelineCreate(
            guideline_type="frequency",
            target_type="food_group",
            target_key="red_meat",
            description="Red meat at most twice per week",
            period="week",
            maximum_occurrences=2,
            is_mandatory=True,
        ),
    )
    update_nutrition_plan(
        db_session,
        plan=plan,
        data=NutritionPlanUpdate(status="active"),
    )


def test_weekly_frequency_progress_counts_person_specific_structured_evidence(
    db_session: Session,
) -> None:
    family, person, other = _setup_people(db_session)
    fish = _food(
        db_session,
        family=family,
        key="dish:fish",
        name="Fish plate",
        protein="fish",
    )
    beef = _food(
        db_session,
        family=family,
        key="dish:beef",
        name="Beef plate",
        protein="red_meat",
    )
    unknown = _food(
        db_session,
        family=family,
        key="dish:unknown",
        name="Unclassified plate",
        protein=None,
    )
    _activate_frequency_plan(db_session, person)

    _meal(
        db_session,
        family=family,
        person=person,
        scheduled_at=datetime(2026, 9, 14, 13, 0, tzinfo=LISBON),
        food=fish,
        event_status="completed",
        participant_status="consumed",
        serving_status="consumed",
    )
    _meal(
        db_session,
        family=family,
        person=person,
        scheduled_at=datetime(2026, 9, 15, 13, 0, tzinfo=LISBON),
        food=fish,
    )
    for day, status in ((16, "completed"), (17, "planned"), (18, "planned")):
        _meal(
            db_session,
            family=family,
            person=person,
            scheduled_at=datetime(2026, 9, day, 13, 0, tzinfo=LISBON),
            food=beef,
            event_status=status,
            participant_status="consumed" if status == "completed" else "planned",
            serving_status="consumed" if status == "completed" else "planned",
        )
    _meal(
        db_session,
        family=family,
        person=person,
        scheduled_at=datetime(2026, 9, 19, 13, 0, tzinfo=LISBON),
        food=unknown,
    )

    shared = _meal(
        db_session,
        family=family,
        person=person,
        scheduled_at=datetime(2026, 9, 20, 13, 0, tzinfo=LISBON),
        food=fish,
    )
    other_participant = MealParticipant(
        meal_event=shared,
        person_id=other.id,
        status="planned",
    )
    other_participant.servings.append(
        Serving(
            food_item_id=beef.id,
            item_type="dish",
            item_key=beef.catalog_key,
            item_name=beef.name,
            status="planned",
            nutrition_source="estimated",
        )
    )
    db_session.add(other_participant)

    _meal(
        db_session,
        family=family,
        person=person,
        scheduled_at=datetime(2026, 9, 20, 15, 0, tzinfo=LISBON),
        food=fish,
        event_status="cancelled",
    )
    _meal(
        db_session,
        family=family,
        person=person,
        scheduled_at=datetime(2026, 9, 20, 16, 0, tzinfo=LISBON),
        food=fish,
        event_status="replaced",
    )
    # 23:30 UTC on Sunday is 00:30 Monday in Lisbon, therefore next week.
    _meal(
        db_session,
        family=family,
        person=person,
        scheduled_at=datetime(2026, 9, 20, 23, 30, tzinfo=UTC),
        food=fish,
    )
    db_session.commit()

    result = get_weekly_frequency_progress(
        db_session,
        person_id=person.id,
        anchor_date=date(2026, 9, 16),
    )

    assert result.week_start == date(2026, 9, 14)
    assert result.week_end == date(2026, 9, 20)
    assert len(result.guidelines) == 2
    by_key = {guideline.target_key: guideline for guideline in result.guidelines}

    fish_progress = by_key["fish"]
    assert fish_progress.completed_occurrences == 1
    assert fish_progress.planned_occurrences == 2
    assert fish_progress.total_occurrences == 3
    assert fish_progress.remaining_minimum == 0
    assert fish_progress.state == "achieved"
    assert fish_progress.unclassified_meal_count == 1
    assert fish_progress.counts_are_lower_bound
    assert all("primary_protein" in item.matched_by for item in fish_progress.occurrences)

    red_meat_progress = by_key["red_meat"]
    assert red_meat_progress.completed_occurrences == 1
    assert red_meat_progress.planned_occurrences == 2
    assert red_meat_progress.total_occurrences == 3
    assert red_meat_progress.remaining_capacity == 0
    assert red_meat_progress.state == "exceeded"
    assert red_meat_progress.unclassified_meal_count == 1
    assert red_meat_progress.counts_are_lower_bound


def test_weekly_frequency_progress_keeps_unsupported_targets_unknown(
    db_session: Session,
) -> None:
    _family, person, _other = _setup_people(db_session)
    plan = create_nutrition_plan(
        db_session,
        person=person,
        data=NutritionPlanCreate(
            title="Unsupported weekly guidance",
            source_type="nutritionist",
            valid_from=date(2026, 9, 1),
        ),
    )
    add_nutrition_plan_guideline(
        db_session,
        plan=plan,
        data=NutritionPlanGuidelineCreate(
            guideline_type="frequency",
            target_type="free_text_category",
            target_key="special-food",
            description="Unsupported structured target",
            period="week",
            minimum_occurrences=2,
        ),
    )
    update_nutrition_plan(
        db_session,
        plan=plan,
        data=NutritionPlanUpdate(status="active"),
    )

    result = get_weekly_frequency_progress(
        db_session,
        person_id=person.id,
        anchor_date=date(2026, 9, 16),
    )

    progress = result.guidelines[0]
    assert progress.evidence_status == "unsupported_target"
    assert progress.state == "unknown"
    assert progress.total_occurrences == 0
    assert progress.remaining_minimum == 2
    assert not progress.counts_are_lower_bound
