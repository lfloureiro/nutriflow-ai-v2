import uuid
from datetime import timedelta

from sqlalchemy.orm import Session

from app.models.family import Family
from app.schemas.shared_practical_recommendation import SharedPracticalRecommendationCreate
from app.schemas.weekly_planning import (
    SharedWeeklyPlanChoiceRead,
    SharedWeeklyPlanningSlotCreate,
    SharedWeeklyPlanParticipantRead,
    SharedWeeklyPlanProposalCreate,
    SharedWeeklyPlanProposalRead,
    SharedWeeklyPlanSelectionRead,
)
from app.services.shared_practical_recommendation_api import (
    compute_shared_practical_recommendation,
)
from app.services.shared_weekly_multi_slot_planning import (
    SharedWeeklyMultiSlotPlanningError,
    SharedWeeklyPlanningCandidate,
    SharedWeeklyPlanningSlot,
    optimize_shared_weekly_slots,
)


class WeeklyPlanningApiError(ValueError):
    pass


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
        result = optimize_shared_weekly_slots(
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
    )
