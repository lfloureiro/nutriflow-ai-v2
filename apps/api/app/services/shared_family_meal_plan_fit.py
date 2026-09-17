import uuid
from dataclasses import replace
from datetime import date

from sqlalchemy.orm import Session

from app.schemas.meal_plan_fit import MealPlanFitRead
from app.schemas.meal_type import MealType
from app.services.meal_recommendation import CandidateEvaluation, MealCandidate
from app.services.meal_recommendation_plan_fit import (
    MealRecommendationPlanFitError,
    evaluate_candidate_plan_fits,
    recommend_meals_with_plan_fit,
)
from app.services.recommendation_practical_plan_fit import (
    recommend_meals_with_practical_context_and_plan_fit,
)
from app.services.recommendation_weekly_frequency import (
    RecommendationWeeklyFrequencyError,
    apply_weekly_frequency_to_recommendation,
    weekly_support_counts,
)
from app.services.shared_family_meal import (
    SharedFamilyMealError,
    SharedFamilyMealRecommendationResult,
    SharedMealCandidateEvaluation,
    SharedMealCandidateProposal,
    SharedMealParticipantContext,
    SharedMealParticipantEvaluation,
    SharedMealPortion,
    _build_candidate,
    _participant_exclusions,
    _portion_map,
    _proposal_identity,
    _score_summary,
    _validate_participants,
    shared_candidate_ranking_key,
)


def _evaluate_participant_candidate(
    participant: SharedMealParticipantContext,
    candidate: MealCandidate,
    *,
    plan_fits: dict[str, MealPlanFitRead],
    planning_date: date,
    engine_version: str,
) -> CandidateEvaluation:
    if participant.practical_context is not None:
        result = recommend_meals_with_practical_context_and_plan_fit(
            candidates=[candidate],
            plan_fits=plan_fits,
            preferences=list(participant.preferences),
            adverse_reactions=list(participant.adverse_reactions),
            planning_date=planning_date,
            practical_context=participant.practical_context,
            practical_profiles=participant.practical_profiles,
            engine_version=engine_version,
        )
    else:
        result = recommend_meals_with_plan_fit(
            candidates=[candidate],
            plan_fits=plan_fits,
            preferences=list(participant.preferences),
            adverse_reactions=list(participant.adverse_reactions),
            planning_date=planning_date,
            engine_version=engine_version,
        )

    try:
        result = apply_weekly_frequency_to_recommendation(
            result,
            plan_fits=plan_fits,
        )
    except RecommendationWeeklyFrequencyError as exc:
        raise SharedFamilyMealError(str(exc)) from exc

    if len(result.evaluations) != 1:
        raise SharedFamilyMealError(
            "Participant Plan-Fit recommendation must return exactly one candidate evaluation."
        )
    return result.evaluations[0]


def _shared_weekly_support(
    candidate_key: str,
    *,
    plan_fits_by_person: dict[uuid.UUID, dict[str, MealPlanFitRead]],
) -> tuple[int, int, int, int]:
    mandatory_participants = 0
    mandatory_total = 0
    advisory_participants = 0
    advisory_total = 0

    for person_fits in plan_fits_by_person.values():
        fit = person_fits.get(candidate_key)
        if fit is None:
            raise SharedFamilyMealError(
                f"Missing Person-specific Plan-Fit evidence for shared candidate {candidate_key!r}."
            )
        mandatory, advisory = weekly_support_counts(fit)
        if mandatory:
            mandatory_participants += 1
            mandatory_total += mandatory
        if advisory:
            advisory_participants += 1
            advisory_total += advisory

    return (
        mandatory_participants,
        mandatory_total,
        advisory_participants,
        advisory_total,
    )


def _has_weekly_guidance(
    plan_fits_by_person: dict[uuid.UUID, dict[str, MealPlanFitRead]],
) -> bool:
    return any(
        guideline.guideline_type == "frequency" and guideline.period == "week"
        for person_fits in plan_fits_by_person.values()
        for fit in person_fits.values()
        for guideline in fit.guideline_results
    )


def recommend_shared_family_meals_with_plan_fit(
    db: Session,
    *,
    participants: tuple[SharedMealParticipantContext, ...],
    proposals: tuple[SharedMealCandidateProposal, ...],
    planning_date: date,
    meal_type: MealType,
    engine_version: str = "shared-family-meal-plan-fit-v1",
) -> SharedFamilyMealRecommendationResult:
    if not engine_version:
        raise SharedFamilyMealError("engine_version must not be empty.")

    family_id = _validate_participants(participants)
    participant_ids = {participant.person.id for participant in participants}
    if None in participant_ids:
        raise SharedFamilyMealError("Shared-family participants must be persisted.")
    typed_participant_ids = {
        person_id for person_id in participant_ids if person_id is not None
    }

    proposal_rows: list[
        tuple[str, str, str, dict[uuid.UUID, SharedMealPortion]]
    ] = []
    candidates_by_person: dict[uuid.UUID, list[MealCandidate]] = {
        person_id: [] for person_id in typed_participant_ids
    }
    candidates_by_person_and_key: dict[tuple[uuid.UUID, str], MealCandidate] = {}
    candidate_keys: set[str] = set()

    for proposal in proposals:
        candidate_key, candidate_name, candidate_kind, catalog_family_id = _proposal_identity(
            proposal
        )
        if candidate_key in candidate_keys:
            raise SharedFamilyMealError(
                f"Duplicate shared-meal candidate key: {candidate_key!r}."
            )
        candidate_keys.add(candidate_key)
        if catalog_family_id is not None and catalog_family_id != family_id:
            raise SharedFamilyMealError(
                "A Family-specific shared-meal candidate belongs to a different Family."
            )

        portions = _portion_map(proposal, typed_participant_ids)
        proposal_rows.append((candidate_key, candidate_name, candidate_kind, portions))
        for person_id, portion in portions.items():
            candidate = _build_candidate(proposal, portion)
            candidates_by_person[person_id].append(candidate)
            candidates_by_person_and_key[(person_id, candidate_key)] = candidate

    plan_fits_by_person: dict[uuid.UUID, dict[str, MealPlanFitRead]] = {}
    for participant in participants:
        person_id = participant.person.id
        state_id = participant.daily_state.id
        if person_id is None or state_id is None:
            raise SharedFamilyMealError(
                "Shared-family Plan-Fit requires persisted Persons and DailyNutritionStates."
            )
        try:
            plan_fits_by_person[person_id] = evaluate_candidate_plan_fits(
                db,
                person_id=person_id,
                daily_nutrition_state_id=state_id,
                planning_date=planning_date,
                meal_type=meal_type,
                candidates=candidates_by_person[person_id],
            )
        except MealRecommendationPlanFitError as exc:
            raise SharedFamilyMealError(str(exc)) from exc

    weekly_guidance = _has_weekly_guidance(plan_fits_by_person)
    provisional: list[SharedMealCandidateEvaluation] = []
    for candidate_key, candidate_name, candidate_kind, portions in proposal_rows:
        participant_evaluations: list[SharedMealParticipantEvaluation] = []
        for participant in participants:
            person_id = participant.person.id
            if person_id is None:
                raise SharedFamilyMealError("Shared-family participant is not persisted.")
            candidate = candidates_by_person_and_key[(person_id, candidate_key)]
            evaluation = _evaluate_participant_candidate(
                participant,
                candidate,
                plan_fits=plan_fits_by_person[person_id],
                planning_date=planning_date,
                engine_version=engine_version,
            )
            participant_evaluations.append(
                SharedMealParticipantEvaluation(
                    person=participant.person,
                    portion=portions[person_id],
                    evaluation=evaluation,
                )
            )

        participant_tuple = tuple(participant_evaluations)
        minimum_score, average_score = _score_summary(participant_tuple)
        eligible = all(item.evaluation.eligible for item in participant_tuple)
        (
            mandatory_participants,
            mandatory_total,
            advisory_participants,
            advisory_total,
        ) = _shared_weekly_support(
            candidate_key,
            plan_fits_by_person=plan_fits_by_person,
        )
        provisional.append(
            SharedMealCandidateEvaluation(
                candidate_key=candidate_key,
                candidate_name=candidate_name,
                candidate_kind=candidate_kind,
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
        )

    eligible_sorted = sorted(
        (evaluation for evaluation in provisional if evaluation.eligible),
        key=shared_candidate_ranking_key,
    )
    rank_by_key = {
        evaluation.candidate_key: rank
        for rank, evaluation in enumerate(eligible_sorted, start=1)
    }

    ranked = [
        replace(evaluation, rank=rank_by_key.get(evaluation.candidate_key))
        for evaluation in provisional
    ]
    ranked.sort(
        key=lambda evaluation: (
            0 if evaluation.eligible else 1,
            evaluation.rank if evaluation.rank is not None else 10**9,
            evaluation.candidate_key,
        )
    )
    result_engine_version = engine_version
    if weekly_guidance:
        result_engine_version = f"{engine_version}+shared-weekly-frequency-v1"
    return SharedFamilyMealRecommendationResult(
        engine_version=result_engine_version,
        evaluations=tuple(ranked),
    )