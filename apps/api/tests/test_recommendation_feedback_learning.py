from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.family import Family
from app.models.person import Person
from app.models.recommendation_feedback import (
    MealRecommendationFeedback,
    MealRecommendationOption,
    MealRecommendationRun,
)
from app.services.meal_recommendation import CandidateEvaluation, MealCandidate, RecommendationResult
from app.services.recommendation_feedback_learning import (
    apply_feedback_to_recommendation,
    load_person_feedback_signals,
)
from app.services.serving_nutrition import NutritionSnapshot

PLANNING_DATE = date(2026, 8, 23)


def _candidate(key: str) -> MealCandidate:
    return MealCandidate(
        key=key,
        name=key,
        kind="recipe",
        quantity=Decimal(1),
        quantity_unit="serving",
        nutrition=NutritionSnapshot(energy_kcal=Decimal(500), nutrients={}),
        subjects=frozenset({("recipe", key)}),
    )


def _evaluation(candidate: MealCandidate) -> CandidateEvaluation:
    return CandidateEvaluation(
        candidate=candidate,
        eligible=True,
        rank=None,
        score=Decimal(1),
        score_breakdown={"energy": Decimal(1)},
        exclusion_reasons=(),
        explanation=(),
    )


def test_feedback_signal_reranks_equal_candidates() -> None:
    accepted = _candidate("recipe:accepted")
    neutral = _candidate("recipe:neutral")
    recommendation = RecommendationResult(
        engine_version="test-v1",
        evaluations=(_evaluation(neutral), _evaluation(accepted)),
    )

    result = apply_feedback_to_recommendation(
        recommendation,
        feedback_signals={accepted.key: Decimal("0.3500")},
    )

    assert result.engine_version == "test-v1+feedback-v1"
    assert result.eligible[0].candidate.key == accepted.key
    assert result.eligible[0].score_breakdown["feedback_history"] == Decimal("0.3500")
    assert "feedback_history: previous choices support this option" in result.eligible[0].explanation


def test_loader_uses_latest_feedback_event_per_option(db_session: Session) -> None:
    family = Family(name="Feedback family", timezone="Europe/Lisbon")
    person = Person(
        family=family,
        first_name="Ana",
        preferred_locale="pt-PT",
        timezone="Europe/Lisbon",
    )
    run = MealRecommendationRun(
        person=person,
        planning_date=PLANNING_DATE - timedelta(days=5),
        meal_type="dinner",
        engine_version="test-v1",
    )
    option = MealRecommendationOption(
        recommendation_run=run,
        candidate_key="recipe:history",
        candidate_name="History",
        candidate_kind="recipe",
        quantity=Decimal(1),
        quantity_unit="serving",
        eligible=True,
        rank=1,
        score=Decimal(1),
        score_breakdown={},
        exclusion_reasons=[],
        explanation=[],
        candidate_subjects=[],
        nutrition_snapshot={},
    )
    old_feedback = MealRecommendationFeedback(
        recommendation_option=option,
        action="accepted",
        source="test",
        recorded_at=datetime(2026, 8, 18, 10, 0, tzinfo=UTC),
    )
    latest_feedback = MealRecommendationFeedback(
        recommendation_option=option,
        action="rejected",
        source="test",
        recorded_at=datetime(2026, 8, 18, 11, 0, tzinfo=UTC),
    )
    db_session.add_all([family, old_feedback, latest_feedback])
    db_session.flush()

    signals = load_person_feedback_signals(
        db_session,
        person_id=person.id,
        planning_date=PLANNING_DATE,
    )

    assert signals == {"recipe:history": Decimal("-0.3000")}
