import uuid
from decimal import Decimal

from app.models.person import Person
from app.services.meal_recommendation import CandidateEvaluation, MealCandidate
from app.services.recommendation_feedback_learning import (
    apply_feedback_to_shared_recommendation,
)
from app.services.serving_nutrition import NutritionSnapshot
from app.services.shared_family_meal import (
    SharedFamilyMealRecommendationResult,
    SharedMealCandidateEvaluation,
    SharedMealParticipantEvaluation,
    SharedMealPortion,
)


def _person() -> Person:
    return Person(
        id=uuid.uuid4(),
        family_id=uuid.uuid4(),
        first_name="Ana",
        preferred_locale="pt-PT",
        timezone="Europe/Lisbon",
    )


def _candidate(key: str) -> MealCandidate:
    return MealCandidate(
        key=key,
        name=key,
        kind="food_item",
        quantity=Decimal(100),
        quantity_unit="g",
        nutrition=NutritionSnapshot(energy_kcal=Decimal(400), nutrients={}),
        subjects=frozenset({("food", key)}),
    )


def _shared_evaluation(
    person: Person,
    *,
    key: str,
    score: Decimal,
    mandatory_support_participants: int = 0,
) -> SharedMealCandidateEvaluation:
    candidate = _candidate(key)
    participant = SharedMealParticipantEvaluation(
        person=person,
        portion=SharedMealPortion(
            person_id=person.id,
            quantity=Decimal(100),
            quantity_unit="g",
        ),
        evaluation=CandidateEvaluation(
            candidate=candidate,
            eligible=True,
            rank=None,
            score=score,
            score_breakdown={"base": score},
            exclusion_reasons=(),
            explanation=(),
        ),
    )
    return SharedMealCandidateEvaluation(
        candidate_key=key,
        candidate_name=key,
        candidate_kind="food_item",
        eligible=True,
        rank=None,
        minimum_score=score,
        average_score=score,
        participant_evaluations=(participant,),
        exclusion_reasons=(),
        weekly_mandatory_support_participants=mandatory_support_participants,
        weekly_mandatory_support_total=mandatory_support_participants,
    )


def test_shared_weekly_support_remains_ahead_of_feedback_score() -> None:
    person = _person()
    weekly = _shared_evaluation(
        person,
        key="dish:weekly",
        score=Decimal("1.0000"),
        mandatory_support_participants=1,
    )
    feedback = _shared_evaluation(
        person,
        key="dish:feedback",
        score=Decimal("1.2000"),
    )
    recommendation = SharedFamilyMealRecommendationResult(
        engine_version="test-v1+shared-weekly-frequency-v1+diversity-v1",
        evaluations=(feedback, weekly),
    )

    result = apply_feedback_to_shared_recommendation(
        recommendation,
        feedback_signals_by_person={
            person.id: {"dish:feedback": Decimal("0.3500")}
        },
    )

    assert result.engine_version.endswith("+feedback-v1")
    assert [evaluation.candidate_key for evaluation in result.eligible] == [
        "dish:weekly",
        "dish:feedback",
    ]
    assert result.eligible[1].minimum_score == Decimal("1.5500")


def test_shared_feedback_still_reranks_when_weekly_support_is_equal() -> None:
    person = _person()
    alpha = _shared_evaluation(
        person,
        key="dish:alpha",
        score=Decimal("1.0000"),
    )
    beta = _shared_evaluation(
        person,
        key="dish:beta",
        score=Decimal("0.9000"),
    )
    recommendation = SharedFamilyMealRecommendationResult(
        engine_version="test-v1+diversity-v1",
        evaluations=(alpha, beta),
    )

    result = apply_feedback_to_shared_recommendation(
        recommendation,
        feedback_signals_by_person={person.id: {"dish:beta": Decimal("0.3500")}},
    )

    assert [evaluation.candidate_key for evaluation in result.eligible] == [
        "dish:beta",
        "dish:alpha",
    ]
    assert result.eligible[0].minimum_score == Decimal("1.2500")
