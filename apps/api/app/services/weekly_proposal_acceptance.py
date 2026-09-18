from zoneinfo import ZoneInfo

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.family import Family
from app.models.food_catalog import Recipe
from app.schemas.family_meal_plan import (
    MealPlanEntryCreate,
    MealPlanParticipantWrite,
)
from app.schemas.shared_meal_transformation import (
    SharedMealTransformationParticipantCreate,
    SharedMealTransformationPlanCreate,
)
from app.schemas.weekly_planning import (
    SharedWeeklyPlanSlotAcceptanceCreate,
    SharedWeeklyPlanSlotAcceptanceRead,
)
from app.services.family_meal_plan import create_meal_plan_entry
from app.services.meal_transformation import MealTransformationError
from app.services.shared_meal_transformation import plan_shared_meal_transformation
from app.services.weekly_planning_api import (
    WeeklyPlanningApiError,
    propose_shared_weekly_plan,
)


class WeeklyProposalStaleError(WeeklyPlanningApiError):
    pass


def _visible_recipe_for_key(
    session: Session,
    *,
    family_id,
    candidate_key: str,
) -> Recipe | None:
    return session.scalar(
        select(Recipe).where(
            Recipe.recipe_key == candidate_key,
            Recipe.is_active.is_(True),
            or_(Recipe.family_id.is_(None), Recipe.family_id == family_id),
        )
    )


def _assert_expected_transformation(
    data: SharedWeeklyPlanSlotAcceptanceCreate,
    choice,
) -> None:
    expected_pair = (
        data.expected_recipe_ingredient_id,
        data.expected_replacement_food_item_id,
    )
    transformation = choice.transformation

    if expected_pair == (None, None):
        if transformation is not None:
            raise WeeklyProposalStaleError(
                "The weekly proposal changed from the base recipe to an adapted recipe; "
                "recalculate before accepting."
            )
        return

    if transformation is None:
        raise WeeklyProposalStaleError(
            "The weekly proposal no longer contains the reviewed recipe adaptation; "
            "recalculate before accepting."
        )

    actual_pair = (
        transformation.operation.recipe_ingredient_id,
        transformation.operation.replacement_food_item_id,
    )
    if actual_pair != expected_pair:
        raise WeeklyProposalStaleError(
            "The weekly recipe adaptation changed while it was being reviewed; "
            "recalculate before accepting."
        )


def accept_shared_weekly_plan_slot(
    session: Session,
    *,
    family: Family,
    data: SharedWeeklyPlanSlotAcceptanceCreate,
) -> SharedWeeklyPlanSlotAcceptanceRead:
    """Recompute and materialize exactly the weekly slot reviewed by the browser.

    Candidate identity and optional transformation identity are treated only as stale-check
    tokens. Nutrition evidence, Plan-Fit, transformation safety and the final selected choice
    are recomputed server-side immediately before persistence.
    """
    proposal = propose_shared_weekly_plan(session, family=family, data=data.proposal)
    if proposal.selected_plan is None:
        raise WeeklyProposalStaleError(
            "The weekly proposal is no longer feasible; recalculate it before accepting."
        )

    choice = next(
        (
            item
            for item in proposal.selected_plan.choices
            if item.slot_key == data.slot_key
        ),
        None,
    )
    if choice is None:
        raise WeeklyProposalStaleError(
            "The selected meal slot is no longer part of the weekly proposal."
        )
    if choice.candidate_key != data.expected_candidate_key:
        raise WeeklyProposalStaleError(
            "The weekly proposal changed while it was being reviewed; "
            "recalculate before accepting."
        )
    _assert_expected_transformation(data, choice)

    if choice.candidate_kind != "recipe":
        raise WeeklyPlanningApiError(
            "Only recipe-backed weekly choices can currently be materialized."
        )

    request_slot = next(
        (slot for slot in data.proposal.slots if slot.slot_key == data.slot_key),
        None,
    )
    if request_slot is None:
        raise WeeklyProposalStaleError(
            "The accepted slot is missing from the original planning request."
        )

    if choice.transformation is not None:
        participants = [
            SharedMealTransformationParticipantCreate(
                person_id=participant.person_id,
                daily_nutrition_state_id=None,
                quantity=participant.quantity,
                quantity_unit=participant.quantity_unit,
            )
            for participant in choice.participants
        ]
        try:
            planned = plan_shared_meal_transformation(
                session,
                family_id=family.id,
                data=SharedMealTransformationPlanCreate(
                    planning_date=choice.planning_date,
                    meal_type=choice.meal_type,
                    recipe_id=choice.transformation.recipe_id,
                    participants=participants,
                    recipe_ingredient_id=(
                        choice.transformation.operation.recipe_ingredient_id
                    ),
                    replacement_food_item_id=(
                        choice.transformation.operation.replacement_food_item_id
                    ),
                    scheduled_at=choice.scheduled_at,
                    title=choice.candidate_name,
                    location=request_slot.location,
                    notes="Aceite a partir de uma proposta semanal NutriFlow.",
                ),
            )
        except MealTransformationError as exc:
            raise WeeklyProposalStaleError(
                "The reviewed weekly recipe adaptation is no longer safe or available; "
                "recalculate before accepting."
            ) from exc
        return SharedWeeklyPlanSlotAcceptanceRead(
            meal_event_id=planned.meal_event_id,
            status=planned.status,
            candidate_key=choice.candidate_key,
            transformation_application_id=planned.transformation_application_id,
        )

    recipe = _visible_recipe_for_key(
        session,
        family_id=family.id,
        candidate_key=choice.candidate_key,
    )
    if recipe is None:
        raise WeeklyProposalStaleError(
            "The selected recipe is no longer available to this Family."
        )

    local_time = (
        choice.scheduled_at.astimezone(ZoneInfo(family.timezone))
        .timetz()
        .replace(tzinfo=None)
    )
    entry = create_meal_plan_entry(
        session,
        family,
        MealPlanEntryCreate(
            date=choice.planning_date,
            meal_type=choice.meal_type,
            local_time=local_time,
            recipe_id=recipe.id,
            participants=[
                MealPlanParticipantWrite(
                    person_id=participant.person_id,
                    quantity=participant.quantity,
                    unit=participant.quantity_unit,
                )
                for participant in choice.participants
            ],
            location=request_slot.location,
            notes="Aceite a partir de uma proposta semanal NutriFlow.",
        ),
    )
    return SharedWeeklyPlanSlotAcceptanceRead(
        meal_event_id=entry.id,
        status=entry.status,
        candidate_key=choice.candidate_key,
        transformation_application_id=None,
    )
