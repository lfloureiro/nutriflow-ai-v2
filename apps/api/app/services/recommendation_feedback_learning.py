import uuid
from dataclasses import replace
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.recommendation_feedback import (
    MealRecommendationFeedback,
    MealRecommendationOption,
    MealRecommendationRun,
)
from app.services.meal_recommendation import CandidateEvaluation, RecommendationResult
from app.services.shared_family_meal import (
    SharedFamilyMealRecommendationResult,
    SharedMealCandidateEvaluation,
    SharedMealParticipantEvaluation,
)

ZERO = Decimal(0)
ONE = Decimal(1)
SCORE_QUANTUM = Decimal("0.0001")
FEEDBACK_LOOKBACK_DAYS = 180
_ACTION_SCORE = {
    "accepted": Decimal("0.3500"),
    "modified": Decimal("0.1000"),
    "rejected": Decimal("-0.3000"),
}


def _quantize(value: Decimal) -> Decimal:
    return value.quantize(SCORE_QUANTUM, rounding=ROUND_HALF_UP)


def _recency_weight(days_ago: int) -> Decimal:
    if days_ago <= 30:
        return ONE
    if days_ago <= 90:
        return Decimal("0.6000")
    return Decimal("0.3000")


def load_person_feedback_signals(
    session: Session,
    *,
    person_id: uuid.UUID,
    planning_date: date,
) -> dict[str, Decimal]:
    rows = session.execute(
        select(MealRecommendationFeedback, MealRecommendationOption, MealRecommendationRun)
        .join(
            MealRecommendationOption,
            MealRecommendationOption.id == MealRecommendationFeedback.recommendation_option_id,
        )
        .join(
            MealRecommendationRun,
            MealRecommendationRun.id == MealRecommendationOption.recommendation_run_id,
        )
        .where(
            MealRecommendationRun.person_id == person_id,
            MealRecommendationRun.planning_date <= planning_date,
            MealRecommendationRun.planning_date
            >= planning_date - timedelta(days=FEEDBACK_LOOKBACK_DAYS),
        )
        .order_by(
            MealRecommendationFeedback.recommendation_option_id,
            MealRecommendationFeedback.recorded_at.desc(),
            MealRecommendationFeedback.created_at.desc(),
        )
    ).all()

    latest_by_option: dict[
        uuid.UUID,
        tuple[MealRecommendationFeedback, MealRecommendationOption, MealRecommendationRun],
    ] = {}
    for feedback, option, run in rows:
        latest_by_option.setdefault(option.id, (feedback, option, run))

    scores: dict[str, Decimal] = {}
    for feedback, option, run in latest_by_option.values():
        base = _ACTION_SCORE.get(feedback.action)
        if base is None:
            continue
        days_ago = max(0, (planning_date - run.planning_date).days)
        scores[option.candidate_key] = scores.get(option.candidate_key, ZERO) + (
            base * _recency_weight(days_ago)
        )

    return {
        candidate_key: _quantize(max(-ONE, min(ONE, value)))
        for candidate_key, value in scores.items()
        if value != ZERO
    }


def _feedback_explanation(score: Decimal) -> str:
    return (
        "feedback_history: previous choices support this option"
        if score > ZERO
        else "feedback_history: previous rejections reduce this option"
    )


def _adjust_evaluation(
    evaluation: CandidateEvaluation,
    feedback_score: Decimal,
) -> CandidateEvaluation:
    if not evaluation.eligible or evaluation.score is None or feedback_score == ZERO:
        return evaluation
    breakdown = dict(evaluation.score_breakdown)
    breakdown["feedback_history"] = feedback_score
    return replace(
        evaluation,
        score=_quantize(evaluation.score + feedback_score),
        score_breakdown=breakdown,
        explanation=(*evaluation.explanation, _feedback_explanation(feedback_score)),
    )


def apply_feedback_to_recommendation(
    recommendation: RecommendationResult,
    *,
    feedback_signals: dict[str, Decimal],
) -> RecommendationResult:
    adjusted = [
        _adjust_evaluation(
            evaluation,
            feedback_signals.get(evaluation.candidate.key, ZERO),
        )
        for evaluation in recommendation.evaluations
    ]
    if not any(
        feedback_signals.get(evaluation.candidate.key, ZERO) != ZERO
        for evaluation in recommendation.evaluations
        if evaluation.eligible
    ):
        return recommendation

    eligible = sorted(
        (evaluation for evaluation in adjusted if evaluation.eligible),
        key=lambda evaluation: (-(evaluation.score or ZERO), evaluation.candidate.key),
    )
    rank_by_key = {
        evaluation.candidate.key: rank for rank, evaluation in enumerate(eligible, start=1)
    }
    ranked = tuple(
        replace(evaluation, rank=rank_by_key.get(evaluation.candidate.key))
        for evaluation in sorted(
            adjusted,
            key=lambda evaluation: (
                0 if evaluation.eligible else 1,
                rank_by_key.get(evaluation.candidate.key, 10**9),
                evaluation.candidate.key,
            ),
        )
    )
    return RecommendationResult(
        engine_version=f"{recommendation.engine_version}+feedback-v1",
        evaluations=ranked,
    )


def _participant_feedback(
    participant: SharedMealParticipantEvaluation,
    feedback_signals: dict[str, Decimal],
) -> SharedMealParticipantEvaluation:
    score = feedback_signals.get(participant.evaluation.candidate.key, ZERO)
    return replace(
        participant,
        evaluation=_adjust_evaluation(participant.evaluation, score),
    )


def _shared_score_summary(
    participants: tuple[SharedMealParticipantEvaluation, ...],
) -> tuple[Decimal | None, Decimal | None]:
    if any(not participant.evaluation.eligible for participant in participants):
        return None, None
    scores = [participant.evaluation.score for participant in participants]
    if any(score is None for score in scores):
        return None, None
    typed_scores = [score for score in scores if score is not None]
    minimum = _quantize(min(typed_scores))
    average = _quantize(sum(typed_scores, start=ZERO) / Decimal(len(typed_scores)))
    return minimum, average


def apply_feedback_to_shared_recommendation(
    recommendation: SharedFamilyMealRecommendationResult,
    *,
    feedback_signals_by_person: dict[uuid.UUID, dict[str, Decimal]],
) -> SharedFamilyMealRecommendationResult:
    changed = False
    adjusted: list[SharedMealCandidateEvaluation] = []
    for evaluation in recommendation.evaluations:
        participants = tuple(
            _participant_feedback(
                participant,
                feedback_signals_by_person.get(participant.person.id, {}),
            )
            for participant in evaluation.participant_evaluations
        )
        if any(
            feedback_signals_by_person.get(participant.person.id, {}).get(
                participant.evaluation.candidate.key,
                ZERO,
            )
            != ZERO
            for participant in evaluation.participant_evaluations
        ):
            changed = True
        minimum, average = _shared_score_summary(participants)
        adjusted.append(
            replace(
                evaluation,
                minimum_score=minimum,
                average_score=average,
                participant_evaluations=participants,
            )
        )

    if not changed:
        return recommendation

    eligible = sorted(
        (evaluation for evaluation in adjusted if evaluation.eligible),
        key=lambda evaluation: (
            -(evaluation.minimum_score or ZERO),
            -(evaluation.average_score or ZERO),
            evaluation.candidate_key,
        ),
    )
    rank_by_key = {
        evaluation.candidate_key: rank for rank, evaluation in enumerate(eligible, start=1)
    }
    ranked = tuple(
        replace(evaluation, rank=rank_by_key.get(evaluation.candidate_key))
        for evaluation in sorted(
            adjusted,
            key=lambda evaluation: (
                0 if evaluation.eligible else 1,
                rank_by_key.get(evaluation.candidate_key, 10**9),
                evaluation.candidate_key,
            ),
        )
    )
    return SharedFamilyMealRecommendationResult(
        engine_version=f"{recommendation.engine_version}+feedback-v1",
        evaluations=ranked,
    )
