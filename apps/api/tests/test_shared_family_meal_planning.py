from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.models.daily_nutrition_state import DailyNutritionState
from app.models.family import Family
from app.models.food_adverse_reaction import FoodAdverseReaction
from app.models.food_catalog import FoodCompositionSnapshot, FoodItem, FoodNutrientComponent
from app.models.person import Person
from app.services.shared_family_meal import (
    SharedMealCandidateProposal,
    SharedMealParticipantContext,
    SharedMealPortion,
    recommend_shared_family_meals,
)
from app.services.shared_family_meal_planning import (
    SharedFamilyMealPlanningError,
    materialize_shared_family_recommendation,
)

PLANNING_DATE = date(2026, 8, 22)


def _daily_state(person: Person, remaining_energy: str) -> DailyNutritionState:
    if person.id is None:
        raise AssertionError("Test Person must be persisted.")
    return DailyNutritionState(
        person_id=person.id,
        state_date=PLANNING_DATE,
        timezone="Europe/Lisbon",
        energy_consumed_kcal=Decimal("1000.00"),
        energy_planned_kcal=Decimal("0.00"),
        energy_remaining_min_kcal=Decimal(remaining_energy),
        energy_remaining_max_kcal=Decimal(remaining_energy),
        calculation_version="test-daily-v1",
    )


def _persisted_shared_recommendation(
    db_session: Session,
    *,
    second_person_allergic: bool = False,
):
    family = Family(name="Shared Planning Family", timezone="Europe/Lisbon")
    first = Person(
        family=family,
        first_name="Ana",
        preferred_locale="pt-PT",
        timezone="Europe/Lisbon",
    )
    second = Person(
        family=family,
        first_name="Bruno",
        preferred_locale="pt-PT",
        timezone="Europe/Lisbon",
    )
    food = FoodItem(
        family=family,
        catalog_key="family:shared:pasta",
        name="Family pasta",
        food_kind="ingredient",
        source="test",
    )
    composition = FoodCompositionSnapshot(
        food_item=food,
        reference_quantity=Decimal("100.0000"),
        reference_unit="g",
        energy_kcal=Decimal("200.0000"),
        data_version="test-v1",
        source="test",
        effective_at=datetime(2026, 8, 21, tzinfo=UTC),
        nutrients=[
            FoodNutrientComponent(
                nutrient_key="protein",
                value=Decimal("10.0000"),
                unit="g",
            )
        ],
    )
    db_session.add(family)
    db_session.flush()

    if first.id is None or second.id is None:
        raise AssertionError("Test Persons must be persisted.")

    second_reactions: tuple[FoodAdverseReaction, ...] = ()
    if second_person_allergic:
        second_reactions = (
            FoodAdverseReaction(
                reaction_type="allergy",
                subject_type="ingredient",
                subject_key=food.catalog_key,
                severity="severe",
                is_mandatory=True,
                source="test",
            ),
        )

    participants = (
        SharedMealParticipantContext(
            person=first,
            daily_state=_daily_state(first, "400.00"),
        ),
        SharedMealParticipantContext(
            person=second,
            daily_state=_daily_state(second, "200.00"),
            adverse_reactions=second_reactions,
        ),
    )
    proposal = SharedMealCandidateProposal(
        portions=(
            SharedMealPortion(
                person_id=first.id,
                quantity=Decimal("200.0000"),
                quantity_unit="g",
            ),
            SharedMealPortion(
                person_id=second.id,
                quantity=Decimal("100.0000"),
                quantity_unit="g",
            ),
        ),
        food_composition=composition,
    )
    recommendation = recommend_shared_family_meals(
        participants=participants,
        proposals=(proposal,),
        planning_date=PLANNING_DATE,
    )
    return recommendation, family, first, second, composition


def test_materialization_creates_one_event_with_person_specific_servings(
    db_session: Session,
) -> None:
    recommendation, family, first, second, composition = _persisted_shared_recommendation(
        db_session
    )

    result = materialize_shared_family_recommendation(
        db_session,
        recommendation=recommendation,
        candidate_key="family:shared:pasta",
        scheduled_at=datetime(2026, 8, 22, 19, 30, tzinfo=UTC),
        timezone="Europe/Lisbon",
        meal_type="dinner",
        location="Home",
    )
    db_session.flush()

    assert result.meal_event.family_id == family.id
    assert result.meal_event.meal_type == "dinner"
    assert result.meal_event.status == "planned"
    assert len(result.participants) == 2
    assert all(
        participant.meal_participant.meal_event is result.meal_event
        for participant in result.participants
    )

    by_person = {participant.person.id: participant for participant in result.participants}
    first_plan = by_person[first.id]
    second_plan = by_person[second.id]

    assert first_plan.serving.quantity_planned == Decimal("200.0000")
    assert first_plan.serving.energy_planned_kcal == Decimal("400.00")
    assert first_plan.serving.nutrition_components[0].planned_value == Decimal("20.0000")
    assert second_plan.serving.quantity_planned == Decimal("100.0000")
    assert second_plan.serving.energy_planned_kcal == Decimal("200.00")
    assert second_plan.serving.nutrition_components[0].planned_value == Decimal("10.0000")
    assert all(serving.food_composition_snapshot is composition for serving in result.servings)


def test_materialization_rejects_ineligible_shared_candidate(db_session: Session) -> None:
    recommendation, _, _, _, _ = _persisted_shared_recommendation(
        db_session,
        second_person_allergic=True,
    )

    with pytest.raises(SharedFamilyMealPlanningError, match="ineligible"):
        materialize_shared_family_recommendation(
            db_session,
            recommendation=recommendation,
            candidate_key="family:shared:pasta",
            scheduled_at=datetime(2026, 8, 22, 19, 30, tzinfo=UTC),
            timezone="Europe/Lisbon",
            meal_type="dinner",
        )


def test_materialization_requires_timezone_aware_schedule(db_session: Session) -> None:
    recommendation, _, _, _, _ = _persisted_shared_recommendation(db_session)

    with pytest.raises(SharedFamilyMealPlanningError, match="timezone-aware"):
        materialize_shared_family_recommendation(
            db_session,
            recommendation=recommendation,
            candidate_key="family:shared:pasta",
            scheduled_at=datetime.fromisoformat("2026-08-22T19:30:00"),
            timezone="Europe/Lisbon",
            meal_type="dinner",
        )


def test_materialization_requires_persisted_composition(db_session: Session) -> None:
    family = Family(name="Transient Composition Family", timezone="Europe/Lisbon")
    first = Person(
        family=family,
        first_name="Ana",
        preferred_locale="pt-PT",
        timezone="Europe/Lisbon",
    )
    second = Person(
        family=family,
        first_name="Bruno",
        preferred_locale="pt-PT",
        timezone="Europe/Lisbon",
    )
    db_session.add(family)
    db_session.flush()
    if first.id is None or second.id is None:
        raise AssertionError("Test Persons must be persisted.")

    food = FoodItem(
        catalog_key="food:transient",
        name="Transient food",
        food_kind="ingredient",
        source="test",
    )
    composition = FoodCompositionSnapshot(
        food_item=food,
        reference_quantity=Decimal("100.0000"),
        reference_unit="g",
        energy_kcal=Decimal("200.0000"),
        data_version="test-v1",
        source="test",
        effective_at=datetime(2026, 8, 21, tzinfo=UTC),
    )
    recommendation = recommend_shared_family_meals(
        participants=(
            SharedMealParticipantContext(
                person=first,
                daily_state=_daily_state(first, "200.00"),
            ),
            SharedMealParticipantContext(
                person=second,
                daily_state=_daily_state(second, "200.00"),
            ),
        ),
        proposals=(
            SharedMealCandidateProposal(
                portions=(
                    SharedMealPortion(
                        person_id=first.id,
                        quantity=Decimal("100.0000"),
                        quantity_unit="g",
                    ),
                    SharedMealPortion(
                        person_id=second.id,
                        quantity=Decimal("100.0000"),
                        quantity_unit="g",
                    ),
                ),
                food_composition=composition,
            ),
        ),
        planning_date=PLANNING_DATE,
    )

    with pytest.raises(SharedFamilyMealPlanningError, match="must be persisted"):
        materialize_shared_family_recommendation(
            db_session,
            recommendation=recommendation,
            candidate_key="food:transient",
            scheduled_at=datetime(2026, 8, 22, 19, 30, tzinfo=UTC),
            timezone="Europe/Lisbon",
            meal_type="dinner",
        )
