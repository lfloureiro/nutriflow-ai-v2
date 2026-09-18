import uuid
from dataclasses import replace
from datetime import timedelta

from sqlalchemy.orm import Session

from app.models.family import Family
from app.models.food_catalog import FoodItem
from app.schemas.shared_meal_transformation import (
    SharedMealTransformationCreate,
    SharedMealTransformationParticipantCreate,
)
from app.schemas.shared_practical_recommendation import SharedPracticalRecommendationCreate
from app.schemas.weekly_planning import (
    SharedWeeklyPlanChoiceRead,
    SharedWeeklyPlanningSlotCreate,
    SharedWeeklyPlanParticipantRead,
    SharedWeeklyPlanProposalCreate,
    SharedWeeklyPlanProposalRead,
    SharedWeeklyPlanTransformationRead,
    SharedWeeklyPlanSelectionRead,
)
from app.services.serving_nutrition import NutrientSnapshot, NutritionSnapshot
from app.services.shared_family_meal import (
    SharedMealCandidateEvaluation,
    SharedMealParticipantEvaluation,
    _participant_exclusions,
    _score_summary,
)
from app.services.shared_family_meal_plan_fit import (
    _evaluate_participant_candidate,
)
from app.services.recommendation_weekly_frequency import weekly_support_counts
from app.services.shared_meal_transformation import (
    _transformed_subjects,
    propose_shared_meal_transformations,
)
from app.services.shared_practical_recommendation_api import (
    compute_shared_practical_recommendation_with_contexts,
)
from app.services.shared_weekly_multi_slot_planning import (
    SharedWeeklyMultiSlotPlanningError,
    SharedWeeklyPlanningCandidate,
    SharedWeeklyPlanningSlot,
)
from app.services.shared_weekly_search import optimize_shared_weekly_slots_scalable


class WeeklyPlanningApiError(ValueError):
    pass


def _transformation_variant_key(
    candidate_key: str,
    *,
    recipe_ingredient_id: uuid.UUID,
    replacement_food_item_id: uuid.UUID,
) -> str:
    return (
        f"{candidate_key}::replace:"
        f"{recipe_ingredient_id}:{replacement_food_item_id}"
    )


def _transformed_weekly_candidate(
    session: Session,
    *,
    original: SharedWeeklyPlanningCandidate,
    contexts_by_person_id,
    proposal,
    planning_date,
    engine_version: str,
) -> SharedWeeklyPlanningCandidate | None:
    by_person = {item.person_id: item for item in proposal.participant_results}
    transformed_participants: list[SharedMealParticipantEvaluation] = []
    plan_fits = []

    for participant in original.evaluation.participant_evaluations:
        person_id = participant.person.id
        source_candidate = participant.evaluation.candidate
        if person_id is None or source_candidate.recipe is None:
            return None
        transformed = by_person.get(person_id)
        context = contexts_by_person_id.get(person_id)
        if transformed is None or context is None or not transformed.after_fit.eligible:
            return None

        replacement = session.get(
            FoodItem,
            proposal.operation.replacement_food_item_id,
        )
        if replacement is None:
            return None

        transformed_candidate = replace(
            source_candidate,
            nutrition=NutritionSnapshot(
                energy_kcal=transformed.after_fit.candidate.nutrition.energy_kcal,
                nutrients={
                    key: NutrientSnapshot(value=value.value, unit=value.unit)
                    for key, value in transformed.after_fit.candidate.nutrition.nutrients.items()
                },
            ),
            subjects=_transformed_subjects(
                source_candidate.recipe,
                source_ingredient_id=proposal.operation.recipe_ingredient_id,
                replacement=replacement,
            ),
        )
        evaluation = _evaluate_participant_candidate(
            context,
            transformed_candidate,
            plan_fits={source_candidate.key: transformed.after_fit},
            planning_date=planning_date,
            engine_version=f"{engine_version}+shared-transformation-v1",
        )
        transformed_participants.append(
            SharedMealParticipantEvaluation(
                person=participant.person,
                portion=participant.portion,
                evaluation=evaluation,
                plan_fit=transformed.after_fit,
            )
        )
        plan_fits.append(transformed.after_fit)

    participant_tuple = tuple(transformed_participants)
    if not participant_tuple:
        return None
    minimum_score, average_score = _score_summary(participant_tuple)
    eligible = all(item.evaluation.eligible for item in participant_tuple)

    mandatory_participants = 0
    mandatory_total = 0
    advisory_participants = 0
    advisory_total = 0
    for fit in plan_fits:
        mandatory, advisory = weekly_support_counts(fit)
        if mandatory:
            mandatory_participants += 1
            mandatory_total += mandatory
        if advisory:
            advisory_participants += 1
            advisory_total += advisory

    shared_evaluation = SharedMealCandidateEvaluation(
        candidate_key=original.evaluation.candidate_key,
        candidate_name=original.evaluation.candidate_name,
        candidate_kind=original.evaluation.candidate_kind,
        eligible=eligible,
        rank=None,
        minimum_score=minimum_score,
        average_score=average_score,
        participant_evaluations=participant_tuple,
        exclusion_reasons=_participant_exclusions(participant_tuple),
        weekly_mandatory_support_participants=mandatory_participants,
        weekly_mandatory_support_total=mandatory_total,
        weekly_advisory_support_participants=advisory_participants,
        weekly_advisory_support_total=advisory_total,
    )
    return SharedWeeklyPlanningCandidate(
        evaluation=shared_evaluation,
        plan_fits=tuple(plan_fits),
        variant_key=_transformation_variant_key(
            original.evaluation.candidate_key,
            recipe_ingredient_id=proposal.operation.recipe_ingredient_id,
            replacement_food_item_id=proposal.operation.replacement_food_item_id,
        ),
    )


def _transformation_candidates(
    session: Session,
    *,
    family: Family,
    original: SharedWeeklyPlanningCandidate,
    contexts_by_person_id,
    planning_date,
    meal_type,
    engine_version: str,
) -> tuple[
    list[SharedWeeklyPlanningCandidate],
    dict[str, SharedWeeklyPlanTransformationRead],
]:
    evaluation = original.evaluation
    if evaluation.candidate_kind != "recipe":
        return [], {}

    first = evaluation.participant_evaluations[0]
    recipe = first.evaluation.candidate.recipe
    if recipe is None or recipe.id is None:
        return [], {}

    participants: list[SharedMealTransformationParticipantCreate] = []
    for participant in evaluation.participant_evaluations:
        person_id = participant.person.id
        if person_id is None:
            return [], {}
        fit = participant.plan_fit
        participants.append(
            SharedMealTransformationParticipantCreate(
                person_id=person_id,
                daily_nutrition_state_id=(
                    fit.daily_nutrition_state_id if fit is not None else None
                ),
                quantity=participant.portion.quantity,
                quantity_unit=participant.portion.quantity_unit,
            )
        )

    transformed = propose_shared_meal_transformations(
        session,
        family_id=family.id,
        data=SharedMealTransformationCreate(
            planning_date=planning_date,
            meal_type=meal_type,
            recipe_id=recipe.id,
            participants=participants,
            max_proposals=3,
        ),
    )

    candidates: list[SharedWeeklyPlanningCandidate] = []
    metadata: dict[str, SharedWeeklyPlanTransformationRead] = {}
    for proposal in transformed.proposals:
        candidate = _transformed_weekly_candidate(
            session,
            original=original,
            contexts_by_person_id=contexts_by_person_id,
            proposal=proposal,
            planning_date=planning_date,
            engine_version=engine_version,
        )
        if candidate is None or not candidate.evaluation.eligible:
            continue
        candidates.append(candidate)
        metadata[candidate.selection_key] = SharedWeeklyPlanTransformationRead(
            kind=proposal.kind,
            recipe_id=recipe.id,
            operation=proposal.operation,
            plan_improvement_participants=proposal.plan_improvement_participants,
            preference_improvement_participants=(
                proposal.preference_improvement_participants
            ),
            explanation=list(proposal.explanation),
        )
    return candidates, metadata


def _planning_slot(
    session: Session,
    *,
    family: Family,
    person_ids: list[uuid.UUID],
    slot: SharedWeeklyPlanningSlotCreate,
) -> tuple[SharedWeeklyPlanningSlot, str]:
    request = SharedPracticalRecommendationCreate(
        person_ids=person_ids,
        planning_date=slot.planning_date,
        scheduled_at=slot.scheduled_at,
        meal_type=slot.meal_type,
        candidates=slot.candidates,
        location=slot.location,
        available_minutes=slot.available_minutes,
        has_kitchen=slot.has_kitchen,
        source_kinds=slot.source_kinds,
        delivery_provider_keys=slot.delivery_provider_keys,
        provisional_history=slot.provisional_history,
        auto_size_portions=slot.auto_size_portions,
        max_results=None,
    )
    recommendation, _ = compute_shared_practical_recommendation(
        session,
        family=family,
        data=request,
    )

    candidates: list[SharedWeeklyPlanningCandidate] = []
    for evaluation in recommendation.evaluations:
        plan_fits = []
        for participant in evaluation.participant_evaluations:
            if participant.plan_fit is None:
                raise WeeklyPlanningApiError(
                    "Server-authoritative Person Plan-Fit evidence is missing from a shared candidate."
                )
            plan_fits.append(participant.plan_fit)
        candidates.append(
            SharedWeeklyPlanningCandidate(
                evaluation=evaluation,
                plan_fits=tuple(plan_fits),
            )
        )

    return (
        SharedWeeklyPlanningSlot(
            slot_key=slot.slot_key,
            planning_date=slot.planning_date,
            meal_type=slot.meal_type,
            candidates=tuple(candidates),
        ),
        recommendation.engine_version,
    )


def propose_shared_weekly_plan(
    session: Session,
    *,
    family: Family,
    data: SharedWeeklyPlanProposalCreate,
) -> SharedWeeklyPlanProposalRead:
    if family.id is None:
        raise WeeklyPlanningApiError("Weekly planning requires a persisted Family.")
    if len(data.person_ids) != len(set(data.person_ids)):
        raise WeeklyPlanningApiError(
            "Each Person can appear only once in a weekly planning proposal."
        )
    slot_keys = [slot.slot_key for slot in data.slots]
    if len(slot_keys) != len(set(slot_keys)):
        raise WeeklyPlanningApiError("Weekly planning slot keys must be unique.")

    planning_slots: list[SharedWeeklyPlanningSlot] = []
    slot_engine_versions: dict[str, str] = {}
    slots_by_key = {slot.slot_key: slot for slot in data.slots}
    for slot in data.slots:
        planning_slot, engine_version = _planning_slot(
            session,
            family=family,
            person_ids=data.person_ids,
            slot=slot,
        )
        planning_slots.append(planning_slot)
        slot_engine_versions[slot.slot_key] = engine_version

    try:
        result = optimize_shared_weekly_slots_scalable(
            tuple(planning_slots),
            max_combinations=data.max_combinations,
        )
    except SharedWeeklyMultiSlotPlanningError as exc:
        raise WeeklyPlanningApiError(str(exc)) from exc

    if result.family_id != family.id:
        raise WeeklyPlanningApiError(
            "Weekly planning result belongs to a different Family."
        )

    earliest = min(slot.planning_date for slot in data.slots)
    week_start = earliest - timedelta(days=earliest.weekday())
    selected_read: SharedWeeklyPlanSelectionRead | None = None
    if result.selected_plan is not None:
        choice_reads: list[SharedWeeklyPlanChoiceRead] = []
        for choice in result.selected_plan.choices:
            request_slot = slots_by_key[choice.slot_key]
            participant_reads: list[SharedWeeklyPlanParticipantRead] = []
            for participant in choice.candidate.evaluation.participant_evaluations:
                person_id = participant.person.id
                if person_id is None:
                    raise WeeklyPlanningApiError(
                        "Selected weekly planning participant is not persisted."
                    )
                participant_reads.append(
                    SharedWeeklyPlanParticipantRead(
                        person_id=person_id,
                        score=participant.evaluation.score,
                        quantity=participant.portion.quantity,
                        quantity_unit=participant.portion.quantity_unit,
                        energy_kcal=participant.evaluation.candidate.nutrition.energy_kcal,
                        explanation=list(participant.evaluation.explanation),
                    )
                )
            choice_reads.append(
                SharedWeeklyPlanChoiceRead(
                    slot_key=choice.slot_key,
                    planning_date=choice.planning_date,
                    scheduled_at=request_slot.scheduled_at,
                    meal_type=choice.meal_type,
                    candidate_key=choice.candidate.evaluation.candidate_key,
                    candidate_name=choice.candidate.evaluation.candidate_name,
                    candidate_kind=choice.candidate.evaluation.candidate_kind,
                    minimum_score=choice.candidate.evaluation.minimum_score,
                    average_score=choice.candidate.evaluation.average_score,
                    participants=participant_reads,
                    transformations=_weekly_transformations_for_choice(
                        session,
                        family=family,
                        choice=choice,
                        all_choices=result.selected_plan.choices,
                        participant_ids=result.participant_ids,
                        base_plan=result.selected_plan,
                    ),
                )
            )
        selected_read = SharedWeeklyPlanSelectionRead(
            mandatory_support_participants=result.selected_plan.mandatory_support_participants,
            mandatory_support_total=result.selected_plan.mandatory_support_total,
            advisory_support_participants=result.selected_plan.advisory_support_participants,
            advisory_support_total=result.selected_plan.advisory_support_total,
            minimum_participant_score=result.selected_plan.minimum_participant_score,
            average_participant_score=result.selected_plan.average_participant_score,
            repeated_candidate_count=result.selected_plan.repeated_candidate_count,
            choices=choice_reads,
        )

    return SharedWeeklyPlanProposalRead(
        family_id=family.id,
        participant_ids=list(result.participant_ids),
        week_start=week_start,
        week_end=week_start + timedelta(days=6),
        engine_version=result.engine_version,
        slot_engine_versions=slot_engine_versions,
        selected_plan=selected_read,
        evaluated_combinations=result.evaluated_combinations,
        feasible_combinations=result.feasible_combinations,
        rejected_by_person_weekly_maximum=result.rejected_by_person_weekly_maximum,
        rejected_by_person_daily_limit=result.rejected_by_person_daily_limit,
        search_strategy=result.search_strategy,
        search_space_size=result.search_space_size,
        search_truncated=result.search_truncated,
    )
