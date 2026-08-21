from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.daily_nutrition_state import DailyNutritionState
from app.models.meal import Serving
from app.models.person import Person
from app.models.recommendation_feedback import (
    MealRecommendationFeedback,
    MealRecommendationOption,
    MealRecommendationRun,
)
from app.services.meal_recommendation import MealCandidate, RecommendationResult


class RecommendationPersistenceError(ValueError):
    pass


class RecommendationFeedbackError(ValueError):
    pass


def _same_entity(left: object | None, right: object | None) -> bool:
    if left is None or right is None:
        return False
    if left is right:
        return True

    left_id = getattr(left, "id", None)
    right_id = getattr(right, "id", None)
    return left_id is not None and left_id == right_id


def _decimal_text(value: Decimal | None) -> str | None:
    return None if value is None else str(value)


def _nutrition_snapshot(candidate: MealCandidate) -> dict[str, object]:
    nutrition = candidate.nutrition
    return {
        "energy_kcal": _decimal_text(nutrition.energy_kcal),
        "nutrients": {
            key: {
                "value": str(nutrient.value),
                "unit": nutrient.unit,
            }
            for key, nutrient in sorted(nutrition.nutrients.items())
        },
    }


def persist_recommendation_run(
    session: Session,
    *,
    person: Person,
    daily_state: DailyNutritionState | None,
    recommendation: RecommendationResult,
    planning_date: date,
    meal_type: str | None = None,
    context: dict[str, object] | None = None,
) -> MealRecommendationRun:
    if daily_state is not None:
        state_person = daily_state.person
        if state_person is not None and not _same_entity(state_person, person):
            raise RecommendationPersistenceError(
                "DailyNutritionState belongs to a different Person than the recommendation run."
            )
        if (
            daily_state.person_id is not None
            and person.id is not None
            and daily_state.person_id != person.id
        ):
            raise RecommendationPersistenceError(
                "DailyNutritionState belongs to a different Person than the recommendation run."
            )

    run = MealRecommendationRun(
        person=person,
        daily_nutrition_state=daily_state,
        planning_date=planning_date,
        meal_type=meal_type,
        engine_version=recommendation.engine_version,
        context=context,
    )

    for evaluation in recommendation.evaluations:
        candidate = evaluation.candidate
        run.options.append(
            MealRecommendationOption(
                food_item=candidate.food_item,
                recipe=candidate.recipe,
                food_composition_snapshot=candidate.food_composition,
                recipe_composition_snapshot=candidate.recipe_composition,
                candidate_key=candidate.key,
                candidate_name=candidate.name,
                candidate_kind=candidate.kind,
                quantity=candidate.quantity,
                quantity_unit=candidate.quantity_unit,
                eligible=evaluation.eligible,
                rank=evaluation.rank,
                score=evaluation.score,
                score_breakdown={
                    key: str(value)
                    for key, value in sorted(evaluation.score_breakdown.items())
                },
                exclusion_reasons=list(evaluation.exclusion_reasons),
                explanation=list(evaluation.explanation),
                candidate_subjects=[
                    {"type": subject_type, "key": subject_key}
                    for subject_type, subject_key in sorted(candidate.subjects)
                ],
                nutrition_snapshot=_nutrition_snapshot(candidate),
            )
        )

    session.add(run)
    return run


def record_recommendation_feedback(
    session: Session,
    *,
    option: MealRecommendationOption,
    action: str,
    resulting_serving: Serving | None = None,
    source: str = "user",
    metadata: dict[str, object] | None = None,
) -> MealRecommendationFeedback:
    if action not in {"accepted", "rejected", "modified"}:
        raise RecommendationFeedbackError(f"Unsupported recommendation feedback action: {action!r}.")
    if not source:
        raise RecommendationFeedbackError("Recommendation feedback source must not be empty.")
    if not option.eligible:
        raise RecommendationFeedbackError(
            "Feedback can only be recorded for an eligible recommendation option."
        )
    if action == "rejected" and resulting_serving is not None:
        raise RecommendationFeedbackError(
            "Rejected recommendation feedback cannot reference a resulting Serving."
        )

    if resulting_serving is not None:
        option_person = option.recommendation_run.person
        serving_person = resulting_serving.meal_participant.person
        if not _same_entity(option_person, serving_person):
            raise RecommendationFeedbackError(
                "Resulting Serving belongs to a different Person than the recommendation run."
            )

    feedback = MealRecommendationFeedback(
        recommendation_option=option,
        resulting_serving=resulting_serving,
        action=action,
        source=source,
        feedback_metadata=metadata,
    )
    session.add(feedback)
    return feedback
