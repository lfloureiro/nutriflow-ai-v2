from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.meal import MealEvent, MealParticipant, Serving
from app.models.recommendation_feedback import MealRecommendationFeedback, MealRecommendationOption
from app.services.meal_slot import assert_meal_slot_available
from app.services.recommendation_feedback import record_recommendation_feedback
from app.services.serving_nutrition import calculate_serving_nutrition


class RecommendationPlanningError(ValueError):
    pass


@dataclass(frozen=True)
class PlannedRecommendationResult:
    feedback: MealRecommendationFeedback
    meal_event: MealEvent
    participant: MealParticipant
    serving: Serving


def _is_timezone_aware(value: datetime) -> bool:
    return value.tzinfo is not None and value.utcoffset() is not None


def materialize_recommendation_option(
    session: Session,
    *,
    option: MealRecommendationOption,
    action: str,
    scheduled_at: datetime,
    timezone: str,
    quantity: Decimal | None = None,
    quantity_unit: str | None = None,
    meal_type: str | None = None,
    title: str | None = None,
    location: str | None = None,
    notes: str | None = None,
    feedback_source: str = "user",
    feedback_metadata: dict[str, object] | None = None,
    calculation_version: str = "serving-nutrition-v1",
) -> PlannedRecommendationResult:
    if action not in {"accepted", "modified"}:
        raise RecommendationPlanningError(
            "Only accepted or modified recommendation options can create planned meals."
        )
    if not option.eligible:
        raise RecommendationPlanningError(
            "An ineligible recommendation option cannot create a planned meal."
        )
    if not _is_timezone_aware(scheduled_at):
        raise RecommendationPlanningError("scheduled_at must be timezone-aware.")
    if not timezone:
        raise RecommendationPlanningError("timezone must not be empty.")

    resolved_quantity = option.quantity if quantity is None else quantity
    resolved_unit = option.quantity_unit if quantity_unit is None else quantity_unit
    if resolved_quantity <= 0:
        raise RecommendationPlanningError("Planned serving quantity must be positive.")
    if not resolved_unit:
        raise RecommendationPlanningError("Planned serving quantity unit must not be empty.")

    if action == "accepted" and (
        resolved_quantity != option.quantity or resolved_unit != option.quantity_unit
    ):
        raise RecommendationPlanningError(
            "Changing recommendation quantity or unit requires action='modified'."
        )

    recommendation_run = option.recommendation_run
    person = recommendation_run.person
    resolved_meal_type = meal_type or recommendation_run.meal_type
    if not resolved_meal_type:
        raise RecommendationPlanningError(
            "meal_type is required when the recommendation run does not define one."
        )

    assert_meal_slot_available(
        session,
        family_id=person.family_id,
        family_timezone=person.family.timezone,
        scheduled_at=scheduled_at,
        meal_type=resolved_meal_type,
    )

    food_composition = option.food_composition_snapshot
    recipe_composition = option.recipe_composition_snapshot
    if (food_composition is None) == (recipe_composition is None):
        raise RecommendationPlanningError(
            "A recommendation option must reference exactly one composition snapshot to be planned."
        )
    composition = food_composition if food_composition is not None else recipe_composition
    if composition is None:
        raise RecommendationPlanningError("Recommendation composition snapshot is unavailable.")

    event = MealEvent(
        family=person.family,
        meal_type=resolved_meal_type,
        title=title or option.candidate_name,
        scheduled_at=scheduled_at,
        timezone=timezone,
        status="planned",
        location=location,
        source="recommendation",
        notes=notes,
    )
    participant = MealParticipant(
        meal_event=event,
        person=person,
        status="planned",
    )
    serving = Serving(
        meal_participant=participant,
        food_item=option.food_item,
        recipe=option.recipe,
        item_type=option.candidate_kind,
        item_key=option.candidate_key,
        item_name=option.candidate_name,
        status="planned",
        quantity_planned=resolved_quantity,
        quantity_unit=resolved_unit,
        nutrition_source="catalog",
        source_reference=(
            f"recommendation-option:{option.id}" if option.id is not None else None
        ),
    )
    calculate_serving_nutrition(
        serving,
        composition,
        calculation_version=calculation_version,
    )

    session.add(event)
    feedback = record_recommendation_feedback(
        session,
        option=option,
        action=action,
        resulting_serving=serving,
        source=feedback_source,
        metadata=feedback_metadata,
    )

    return PlannedRecommendationResult(
        feedback=feedback,
        meal_event=event,
        participant=participant,
        serving=serving,
    )
