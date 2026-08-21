import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from app.models.daily_nutrition_state import DailyNutritionState
from app.models.food_adverse_reaction import FoodAdverseReaction
from app.models.food_catalog import FoodCompositionSnapshot, FoodItem
from app.models.food_preference import FoodPreference
from app.models.person import Person
from app.models.schedule_entry import ScheduleEntry
from app.services.recommendation_practical_context import PracticalMealContext
from app.services.shared_family_meal import (
    SharedFamilyMealError,
    SharedMealCandidateProposal,
    SharedMealParticipantContext,
    SharedMealPortion,
    recommend_shared_family_meals,
)

PLANNING_DATE = date(2026, 8, 22)
FAMILY_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")


def _participant(
    *,
    person_id: uuid.UUID,
    first_name: str,
    family_id: uuid.UUID = FAMILY_ID,
    remaining_energy: str = "500.00",
    preferences: tuple[FoodPreference, ...] = (),
    adverse_reactions: tuple[FoodAdverseReaction, ...] = (),
    practical_context: PracticalMealContext | None = None,
) -> SharedMealParticipantContext:
    person = Person(
        id=person_id,
        family_id=family_id,
        first_name=first_name,
        preferred_locale="pt-PT",
        timezone="Europe/Lisbon",
    )
    daily_state = DailyNutritionState(
        person_id=person_id,
        state_date=PLANNING_DATE,
        timezone="Europe/Lisbon",
        energy_consumed_kcal=Decimal("1000.00"),
        energy_planned_kcal=Decimal("0.00"),
        energy_remaining_min_kcal=Decimal(remaining_energy),
        energy_remaining_max_kcal=Decimal(remaining_energy),
        calculation_version="test-daily-v1",
    )
    return SharedMealParticipantContext(
        person=person,
        daily_state=daily_state,
        preferences=preferences,
        adverse_reactions=adverse_reactions,
        practical_context=practical_context,
    )


def _proposal(
    *,
    key: str,
    name: str,
    energy_per_100g: str,
    portions: tuple[tuple[uuid.UUID, str], ...],
) -> SharedMealCandidateProposal:
    food = FoodItem(
        catalog_key=key,
        name=name,
        food_kind="ingredient",
        source="test",
    )
    composition = FoodCompositionSnapshot(
        food_item=food,
        reference_quantity=Decimal("100.0000"),
        reference_unit="g",
        energy_kcal=Decimal(energy_per_100g),
        data_version="test-v1",
        source="test",
        effective_at=datetime(2026, 8, 21, tzinfo=UTC),
    )
    return SharedMealCandidateProposal(
        portions=tuple(
            SharedMealPortion(
                person_id=person_id,
                quantity=Decimal(quantity),
                quantity_unit="g",
            )
            for person_id, quantity in portions
        ),
        food_composition=composition,
    )


def test_shared_candidate_uses_person_specific_portions() -> None:
    first_id = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    second_id = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
    participants = (
        _participant(person_id=first_id, first_name="Ana", remaining_energy="500.00"),
        _participant(person_id=second_id, first_name="Bruno", remaining_energy="250.00"),
    )
    proposal = _proposal(
        key="food:shared-pasta",
        name="Shared pasta",
        energy_per_100g="500.0000",
        portions=((first_id, "100.0000"), (second_id, "50.0000")),
    )

    result = recommend_shared_family_meals(
        participants=participants,
        proposals=(proposal,),
        planning_date=PLANNING_DATE,
    )

    shared = result.eligible[0]
    assert shared.rank == 1
    assert shared.minimum_score == Decimal("1.0000")
    assert shared.average_score == Decimal("1.0000")
    first, second = shared.participant_evaluations
    assert first.portion.quantity == Decimal("100.0000")
    assert first.evaluation.candidate.nutrition.energy_kcal == Decimal("500.00")
    assert second.portion.quantity == Decimal("50.0000")
    assert second.evaluation.candidate.nutrition.energy_kcal == Decimal("250.00")


def test_mandatory_reaction_for_one_person_excludes_shared_candidate() -> None:
    first_id = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    second_id = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
    allergy = FoodAdverseReaction(
        reaction_type="allergy",
        subject_type="ingredient",
        subject_key="food:peanut",
        severity="severe",
        is_mandatory=True,
        source="user",
    )
    participants = (
        _participant(person_id=first_id, first_name="Ana"),
        _participant(
            person_id=second_id,
            first_name="Bruno",
            adverse_reactions=(allergy,),
        ),
    )
    proposal = _proposal(
        key="food:peanut",
        name="Peanut dish",
        energy_per_100g="500.0000",
        portions=((first_id, "100.0000"), (second_id, "100.0000")),
    )

    result = recommend_shared_family_meals(
        participants=participants,
        proposals=(proposal,),
        planning_date=PLANNING_DATE,
    )

    assert result.eligible == ()
    evaluation = result.evaluations[0]
    assert evaluation.eligible is False
    assert evaluation.minimum_score is None
    assert evaluation.average_score is None
    assert evaluation.exclusion_reasons == (
        f"person:{second_id}:mandatory_reaction:ingredient:food:peanut",
    )


def test_shared_ranking_prioritizes_worst_served_person_before_average_score() -> None:
    first_id = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    second_id = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
    favorite = FoodPreference(
        subject_type="ingredient",
        subject_key="food:polarizing",
        preference_type="like",
        intensity=5,
        source="user",
    )
    disliked = FoodPreference(
        subject_type="ingredient",
        subject_key="food:polarizing",
        preference_type="dislike",
        intensity=5,
        source="user",
    )
    participants = (
        _participant(
            person_id=first_id,
            first_name="Ana",
            preferences=(favorite,),
        ),
        _participant(
            person_id=second_id,
            first_name="Bruno",
            preferences=(disliked,),
        ),
    )
    polarizing = _proposal(
        key="food:polarizing",
        name="Polarizing meal",
        energy_per_100g="500.0000",
        portions=((first_id, "100.0000"), (second_id, "100.0000")),
    )
    balanced = _proposal(
        key="food:balanced",
        name="Balanced meal",
        energy_per_100g="500.0000",
        portions=((first_id, "100.0000"), (second_id, "100.0000")),
    )

    result = recommend_shared_family_meals(
        participants=participants,
        proposals=(polarizing, balanced),
        planning_date=PLANNING_DATE,
    )

    assert [evaluation.candidate_key for evaluation in result.eligible] == [
        "food:balanced",
        "food:polarizing",
    ]
    assert result.eligible[0].minimum_score == Decimal("1.0000")
    assert result.eligible[0].average_score == Decimal("1.0000")
    assert result.eligible[1].minimum_score == Decimal("0.0000")
    assert result.eligible[1].average_score == Decimal("1.0000")


def test_unavailable_schedule_for_one_person_excludes_shared_candidate() -> None:
    first_id = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    second_id = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
    scheduled_at = datetime(2026, 8, 22, 19, 30, tzinfo=UTC)
    unavailable = ScheduleEntry(
        entry_type="one_off",
        event_type="work",
        availability_effect="unavailable",
        starts_at=datetime(2026, 8, 22, 19, 0, tzinfo=UTC),
        ends_at=datetime(2026, 8, 22, 20, 0, tzinfo=UTC),
        timezone="Europe/Lisbon",
        flexibility_minutes=0,
        source="test",
    )
    participants = (
        _participant(person_id=first_id, first_name="Ana"),
        _participant(
            person_id=second_id,
            first_name="Bruno",
            practical_context=PracticalMealContext(
                scheduled_at=scheduled_at,
                schedule_entries=(unavailable,),
            ),
        ),
    )
    proposal = _proposal(
        key="food:dinner",
        name="Dinner",
        energy_per_100g="500.0000",
        portions=((first_id, "100.0000"), (second_id, "100.0000")),
    )

    result = recommend_shared_family_meals(
        participants=participants,
        proposals=(proposal,),
        planning_date=PLANNING_DATE,
    )

    assert result.eligible == ()
    assert result.evaluations[0].exclusion_reasons == (
        f"person:{second_id}:schedule_unavailable",
    )


def test_shared_recommendation_rejects_people_from_different_families() -> None:
    first_id = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    second_id = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
    participants = (
        _participant(person_id=first_id, first_name="Ana"),
        _participant(
            person_id=second_id,
            first_name="Bruno",
            family_id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
        ),
    )

    with pytest.raises(SharedFamilyMealError, match="same Family"):
        recommend_shared_family_meals(
            participants=participants,
            proposals=(),
            planning_date=PLANNING_DATE,
        )


def test_shared_proposal_requires_one_portion_per_participant() -> None:
    first_id = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    second_id = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
    participants = (
        _participant(person_id=first_id, first_name="Ana"),
        _participant(person_id=second_id, first_name="Bruno"),
    )
    incomplete = _proposal(
        key="food:incomplete",
        name="Incomplete meal",
        energy_per_100g="500.0000",
        portions=((first_id, "100.0000"),),
    )

    with pytest.raises(SharedFamilyMealError, match="exactly one portion"):
        recommend_shared_family_meals(
            participants=participants,
            proposals=(incomplete,),
            planning_date=PLANNING_DATE,
        )
