import uuid

from sqlalchemy.orm import Session, selectinload

from app.models.food_catalog import FoodCompositionSnapshot, RecipeCompositionSnapshot
from app.models.person import Person
from app.models.recommendation_feedback import (
    MealRecommendationOption,
    MealRecommendationRun,
)
from app.schemas.recommendation_decision import (
    RecommendationDecisionCreate,
    RecommendationDecisionRead,
)
from app.services.recommendation_feedback import record_recommendation_feedback
from app.services.recommendation_planning import materialize_recommendation_option
from app.services.serving_nutrition import ServingNutritionCalculationError


class RecommendationDecisionApiError(ValueError):
    pass


class RecommendationDecisionApiNotFoundError(RecommendationDecisionApiError):
    pass


def _load_option(session: Session, option_id: uuid.UUID) -> MealRecommendationOption:
    option = session.get(
        MealRecommendationOption,
        option_id,
        options=(
            selectinload(MealRecommendationOption.recommendation_run)
            .selectinload(MealRecommendationRun.person)
            .selectinload(Person.family),
            selectinload(MealRecommendationOption.food_item),
            selectinload(MealRecommendationOption.recipe),
            selectinload(MealRecommendationOption.food_composition_snapshot).selectinload(
                FoodCompositionSnapshot.nutrients
            ),
            selectinload(MealRecommendationOption.recipe_composition_snapshot).selectinload(
                RecipeCompositionSnapshot.nutrients
            ),
        ),
    )
    if option is None:
        raise RecommendationDecisionApiNotFoundError("Recommendation option not found.")
    return option


def _validate_request(data: RecommendationDecisionCreate) -> None:
    planning_values = (
        data.scheduled_at,
        data.timezone,
        data.quantity,
        data.quantity_unit,
        data.meal_type,
        data.title,
        data.location,
        data.notes,
    )
    if data.action == "rejected":
        if any(value is not None for value in planning_values):
            raise RecommendationDecisionApiError(
                "Rejected recommendation decisions cannot include meal-planning fields."
            )
        return

    if data.scheduled_at is None:
        raise RecommendationDecisionApiError(
            "scheduled_at is required for accepted or modified recommendation decisions."
        )
    if data.timezone is None or not data.timezone:
        raise RecommendationDecisionApiError(
            "timezone is required for accepted or modified recommendation decisions."
        )


def _rejected_response(
    session: Session,
    *,
    option: MealRecommendationOption,
    data: RecommendationDecisionCreate,
) -> RecommendationDecisionRead:
    feedback = record_recommendation_feedback(
        session,
        option=option,
        action="rejected",
        source="user",
        metadata=data.feedback_metadata,
    )
    session.flush()

    if feedback.id is None or option.id is None:
        raise RecommendationDecisionApiError("Recommendation rejection was not persisted.")

    response = RecommendationDecisionRead(
        feedback_id=feedback.id,
        recommendation_option_id=option.id,
        action="rejected",
        resulting_serving_id=None,
        meal_event_id=None,
        meal_event_status=None,
        scheduled_at=None,
        quantity_planned=None,
        quantity_unit=None,
        energy_planned_kcal=None,
    )
    session.commit()
    return response


def create_recommendation_decision(
    session: Session,
    *,
    option_id: uuid.UUID,
    data: RecommendationDecisionCreate,
) -> RecommendationDecisionRead:
    _validate_request(data)
    option = _load_option(session, option_id)

    if data.action == "rejected":
        return _rejected_response(session, option=option, data=data)

    scheduled_at = data.scheduled_at
    timezone = data.timezone
    if scheduled_at is None or timezone is None:
        raise RecommendationDecisionApiError(
            "Accepted or modified recommendation decisions require schedule information."
        )

    try:
        result = materialize_recommendation_option(
            session,
            option=option,
            action=data.action,
            scheduled_at=scheduled_at,
            timezone=timezone,
            quantity=data.quantity,
            quantity_unit=data.quantity_unit,
            meal_type=data.meal_type,
            title=data.title,
            location=data.location,
            notes=data.notes,
            feedback_source="user",
            feedback_metadata=data.feedback_metadata,
        )
    except ServingNutritionCalculationError as exc:
        raise RecommendationDecisionApiError(str(exc)) from exc

    session.flush()
    if (
        option.id is None
        or result.feedback.id is None
        or result.meal_event.id is None
        or result.serving.id is None
    ):
        raise RecommendationDecisionApiError("Recommendation decision was not fully persisted.")

    response = RecommendationDecisionRead(
        feedback_id=result.feedback.id,
        recommendation_option_id=option.id,
        action=data.action,
        resulting_serving_id=result.serving.id,
        meal_event_id=result.meal_event.id,
        meal_event_status=result.meal_event.status,
        scheduled_at=result.meal_event.scheduled_at,
        quantity_planned=result.serving.quantity_planned,
        quantity_unit=result.serving.quantity_unit,
        energy_planned_kcal=result.serving.energy_planned_kcal,
    )
    session.commit()
    return response
