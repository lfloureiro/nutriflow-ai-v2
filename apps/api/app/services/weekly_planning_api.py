import uuid
from collections import Counter
from dataclasses import dataclass, replace
from datetime import timedelta

from sqlalchemy.orm import Session

from app.models.family import Family
from app.models.food_catalog import FoodItem
from app.schemas.shared_meal_transformation import (
    SharedMealTransformationCreate,
    SharedMealTransformationParticipantCreate,
    SharedMealTransformationProposalRead,
)
from app.schemas.shared_practical_recommendation import SharedPracticalRecommendationCreate
from app.schemas.weekly_planning import (
    SharedWeeklyPlanChoiceRead,
    SharedWeeklyPlanCreate,
    SharedWeeklyPlanMaterializedChoiceRead,
    SharedWeeklyPlanningSlotCreate,
    SharedWeeklyPlanParticipantRead,
    SharedWeeklyPlanProposalCreate,
    SharedWeeklyPlanProposalRead,
    SharedWeeklyPlanRead,
    SharedWeeklyPlanSelectionRead,
    SharedWeeklyPlanSkippedSlotRead,
    SharedWeeklyPlanTransformationRead,
)
from app.services.recommendation_weekly_frequency import weekly_support_counts
from app.services.serving_nutrition import NutrientSnapshot, NutritionSnapshot
from app.services.shared_family_meal import (
    SharedFamilyMealRecommendationResult,
    SharedMealCandidateEvaluation,
    SharedMealParticipantEvaluation,
    _participant_exclusions,
    _score_summary,
)
from app.services.shared_family_meal_plan_fit import (
    _evaluate_participant_candidate,
)
from app.services.shared_family_meal_planning import materialize_shared_family_recommendation
from app.services.shared_meal_transformation import (
    _load_variants,
    _transformed_subjects,
    materialize_selected_shared_meal_transformation,
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
from app.services.shared_weekly_search import (
    ENGINE_VERSION as SEARCH_ENGINE_VERSION,
)
from app.services.shared_weekly_search import (
    SharedWeeklySearchResult,
    optimize_shared_weekly_slots_scalable,
)
from app.services.weekly_debug import (
    weekly_debug,
    weekly_debug_span,
    weekly_debug_verbose_enabled,
)
from app.services.weekly_planning_request_cache import (
    current_weekly_planning_cache,
    weekly_planning_cache_scope,
)


class WeeklyPlanningApiError(ValueError):
    pass


class WeeklyPlanningStaleError(WeeklyPlanningApiError):
    pass


@dataclass(frozen=True)
class _WeeklyTransformationEvidence:
    recipe_id: uuid.UUID
    proposal: SharedMealTransformationProposalRead

    def as_read(self) -> SharedWeeklyPlanTransformationRead:
        return SharedWeeklyPlanTransformationRead(
            kind=self.proposal.kind,
            recipe_id=self.recipe_id,
            operation=self.proposal.operation,
            plan_improvement_participants=self.proposal.plan_improvement_participants,
            preference_improvement_participants=(
                self.proposal.preference_improvement_participants
            ),
            explanation=list(self.proposal.explanation),
        )


@dataclass(frozen=True)
class _ComputedWeeklyPlan:
    read: SharedWeeklyPlanProposalRead
    result: SharedWeeklySearchResult
    transformations_by_slot: dict[
        str,
        dict[str, _WeeklyTransformationEvidence],
    ]
    slots_by_key: dict[str, SharedWeeklyPlanningSlotCreate]
    slot_engine_versions: dict[str, str]


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
        planning_category=original.evaluation.planning_category,
        primary_protein=original.evaluation.primary_protein,
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
    dict[str, _WeeklyTransformationEvidence],
]:
    evaluation = original.evaluation
    if evaluation.candidate_kind != "recipe":
        return [], {}

    first = evaluation.participant_evaluations[0]
    recipe = first.evaluation.candidate.recipe
    if recipe is None or recipe.id is None:
        return [], {}

    request_cache = current_weekly_planning_cache(session)
    transformable_key = (family.id, recipe.id)
    has_variants = (
        request_cache.transformable_recipes.get(transformable_key)
        if request_cache is not None
        else None
    )
    if has_variants is None:
        variants, _ = _load_variants(
            session,
            family_id=family.id,
            recipe=recipe,
        )
        has_variants = bool(variants)
        if request_cache is not None:
            request_cache.transformable_recipes[transformable_key] = has_variants
    if not has_variants:
        weekly_debug(
            "TRANSFORM",
            "skip-no-variants",
            candidate=evaluation.candidate_key,
            recipe=recipe.id,
        )
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
        baseline_fits_by_person={
            participant.person.id: participant.plan_fit
            for participant in evaluation.participant_evaluations
            if participant.person.id is not None and participant.plan_fit is not None
        },
    )

    candidates: list[SharedWeeklyPlanningCandidate] = []
    metadata: dict[str, _WeeklyTransformationEvidence] = {}
    for proposal in transformed.proposals:
        candidate = _transformed_weekly_candidate(
            session,
            original=original,
            contexts_by_person_id=contexts_by_person_id,
            proposal=proposal,
            planning_date=planning_date,
            engine_version=engine_version,
        )
        if candidate is None:
            continue
        candidates.append(candidate)
        metadata[candidate.selection_key] = _WeeklyTransformationEvidence(
            recipe_id=recipe.id,
            proposal=proposal,
        )
    return candidates, metadata


def _plan_fit_blocker_labels(fit) -> list[str]:
    labels: list[str] = []
    labels.extend(f"safety:{issue}" for issue in fit.safety_issues)
    labels.extend(
        f"conflict:{conflict.target_type}:{conflict.target_key}"
        for conflict in fit.conflicts
        if conflict.severity == "mandatory"
    )
    labels.extend(
        (
            f"rule:{rule.target_type}:{rule.target_key}:"
            f"{rule.operator}:{rule.scope}:{rule.status}"
        )
        for rule in fit.rule_results
        if rule.is_mandatory and rule.status in {"fail", "unknown", "not_evaluated"}
    )
    labels.extend(
        (
            f"guideline:{guideline.guideline_type}:"
            f"{guideline.target_type or '-'}:{guideline.target_key or '-'}:"
            f"{guideline.status}"
        )
        for guideline in fit.guideline_results
        if guideline.is_mandatory
        and guideline.status in {"fail", "unknown", "not_evaluated"}
    )
    return labels


def _debug_slot_plan_fit(
    *,
    slot_key: str,
    candidates: list[SharedWeeklyPlanningCandidate],
) -> None:
    if not weekly_debug_verbose_enabled():
        return

    by_person: dict[uuid.UUID, list] = {}
    for candidate in candidates:
        for fit in candidate.plan_fits:
            by_person.setdefault(fit.person_id, []).append(fit)

    for person_id, fits in sorted(by_person.items(), key=lambda item: str(item[0])):
        ineligible = [fit for fit in fits if not fit.eligible]
        blocker_counts = Counter(
            label
            for fit in ineligible
            for label in _plan_fit_blocker_labels(fit)
        )
        weekly_debug(
            "PLANFIT-VERBOSE",
            "slot-person-summary",
            slot=slot_key,
            person=person_id,
            candidates=len(fits),
            eligible=sum(fit.eligible for fit in fits),
            ineligible=len(ineligible),
            top_blockers="|".join(
                f"{label}x{count}"
                for label, count in blocker_counts.most_common(12)
            )
            or "none",
        )

    rejected = [
        candidate
        for candidate in candidates
        if not all(fit.eligible for fit in candidate.plan_fits)
    ]
    for candidate in rejected[:8]:
        per_person = []
        for fit in candidate.plan_fits:
            if fit.eligible:
                continue
            labels = _plan_fit_blocker_labels(fit)
            per_person.append(
                f"{fit.person_id}=>"
                + (",".join(labels[:8]) if labels else f"status:{fit.status}")
            )
        weekly_debug(
            "PLANFIT-VERBOSE",
            "candidate-rejected",
            slot=slot_key,
            candidate=candidate.evaluation.candidate_key,
            name=candidate.evaluation.candidate_name,
            blockers=" || ".join(per_person) or "unknown",
        )


def _planning_slot(
    session: Session,
    *,
    family: Family,
    person_ids: list[uuid.UUID],
    slot: SharedWeeklyPlanningSlotCreate,
) -> tuple[
    SharedWeeklyPlanningSlot,
    str,
    dict[str, _WeeklyTransformationEvidence],
]:
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
    with weekly_debug_span(
        "WEEKLY",
        "slot-recommendation",
        slot=slot.slot_key,
        date=slot.planning_date,
        meal_type=slot.meal_type,
        candidates=len(slot.candidates),
        people=len(person_ids),
    ):
        recommendation, _, contexts = compute_shared_practical_recommendation_with_contexts(
            session,
            family=family,
            data=request,
        )
    contexts_by_person_id = {
        context.person.id: context
        for context in contexts
        if context.person.id is not None
    }

    candidates: list[SharedWeeklyPlanningCandidate] = []
    transformation_metadata: dict[str, _WeeklyTransformationEvidence] = {}
    for evaluation in recommendation.evaluations:
        plan_fits = []
        for participant in evaluation.participant_evaluations:
            if participant.plan_fit is None:
                raise WeeklyPlanningApiError(
                    "Server-authoritative Person Plan-Fit evidence is missing from a shared candidate."
                )
            plan_fits.append(participant.plan_fit)

        base_candidate = SharedWeeklyPlanningCandidate(
            evaluation=evaluation,
            plan_fits=tuple(plan_fits),
        )
        candidates.append(base_candidate)

        with weekly_debug_span(
            "TRANSFORM",
            "candidate",
            slot=slot.slot_key,
            candidate=evaluation.candidate_key,
        ):
            transformed_candidates, transformed_metadata = _transformation_candidates(
                session,
                family=family,
                original=base_candidate,
                contexts_by_person_id=contexts_by_person_id,
                planning_date=slot.planning_date,
                meal_type=slot.meal_type,
                engine_version=recommendation.engine_version,
            )
        candidates.extend(transformed_candidates)
        transformation_metadata.update(transformed_metadata)

    eligible_candidates = [
        candidate
        for candidate in candidates
        if candidate.evaluation.eligible and all(fit.eligible for fit in candidate.plan_fits)
    ]
    shared_eligible = sum(1 for candidate in candidates if candidate.evaluation.eligible)
    plan_eligible = sum(
        1 for candidate in candidates if all(fit.eligible for fit in candidate.plan_fits)
    )
    weekly_debug(
        "WEEKLY",
        "slot-ready",
        slot=slot.slot_key,
        candidates=len(candidates),
        eligible=len(eligible_candidates),
        shared_eligible=shared_eligible,
        plan_eligible=plan_eligible,
        transformations=len(transformation_metadata),
    )
    _debug_slot_plan_fit(slot_key=slot.slot_key, candidates=candidates)
    if not eligible_candidates:
        reasons = sorted(
            {
                reason
                for candidate in candidates
                for reason in candidate.evaluation.exclusion_reasons
            }
        )
        weekly_debug(
            "WEEKLY",
            "slot-no-eligible-candidates",
            slot=slot.slot_key,
            reasons="|".join(reasons[:12]) if reasons else "none",
        )

    engine_version = recommendation.engine_version
    if transformation_metadata:
        engine_version = f"{engine_version}+weekly-transformations-v1"

    return (
        SharedWeeklyPlanningSlot(
            slot_key=slot.slot_key,
            planning_date=slot.planning_date,
            meal_type=slot.meal_type,
            candidates=tuple(candidates),
        ),
        engine_version,
        transformation_metadata,
    )


def _compute_shared_weekly_plan_uncached(
    session: Session,
    *,
    family: Family,
    data: SharedWeeklyPlanProposalCreate,
) -> _ComputedWeeklyPlan:
    if family.id is None:
        raise WeeklyPlanningApiError("Weekly planning requires a persisted Family.")
    if len(data.person_ids) != len(set(data.person_ids)):
        raise WeeklyPlanningApiError(
            "Each Person can appear only once in a weekly planning proposal."
        )
    slot_keys = [slot.slot_key for slot in data.slots]
    if len(slot_keys) != len(set(slot_keys)):
        raise WeeklyPlanningApiError("Weekly planning slot keys must be unique.")

    weekly_debug(
        "WEEKLY",
        "proposal-input",
        family=family.id,
        slots=len(data.slots),
        people=len(data.person_ids),
        max_combinations=data.max_combinations,
    )
    planning_slots: list[SharedWeeklyPlanningSlot] = []
    skipped_slots: list[SharedWeeklyPlanSkippedSlotRead] = []
    slot_engine_versions: dict[str, str] = {}
    transformations_by_slot: dict[
        str,
        dict[str, _WeeklyTransformationEvidence],
    ] = {}
    slots_by_key = {slot.slot_key: slot for slot in data.slots}
    for slot in data.slots:
        with weekly_debug_span(
            "WEEKLY",
            "slot",
            slot=slot.slot_key,
            date=slot.planning_date,
            meal_type=slot.meal_type,
            candidates=len(slot.candidates),
        ):
            planning_slot, engine_version, transformation_metadata = _planning_slot(
                session,
                family=family,
                person_ids=data.person_ids,
                slot=slot,
            )
        eligible_candidates = tuple(
            candidate
            for candidate in planning_slot.candidates
            if candidate.evaluation.eligible
            and all(fit.eligible for fit in candidate.plan_fits)
        )
        slot_engine_versions[slot.slot_key] = engine_version
        transformations_by_slot[slot.slot_key] = transformation_metadata
        if not eligible_candidates:
            exclusion_reasons = sorted(
                {
                    reason
                    for candidate in planning_slot.candidates
                    for reason in candidate.evaluation.exclusion_reasons
                }
            )
            skipped_slots.append(
                SharedWeeklyPlanSkippedSlotRead(
                    slot_key=slot.slot_key,
                    planning_date=slot.planning_date,
                    meal_type=slot.meal_type,
                    reason="no_eligible_candidates",
                    exclusion_reasons=exclusion_reasons,
                )
            )
            weekly_debug(
                "WEEKLY",
                "slot-skipped",
                slot=slot.slot_key,
                reason="no_eligible_candidates",
            )
            continue
        planning_slots.append(planning_slot)

    if planning_slots:
        try:
            with weekly_debug_span(
                "SEARCH",
                "weekly-optimization",
                slots=len(planning_slots),
                skipped=len(skipped_slots),
                max_combinations=data.max_combinations,
            ):
                result = optimize_shared_weekly_slots_scalable(
                    tuple(planning_slots),
                    max_combinations=data.max_combinations,
                )
        except SharedWeeklyMultiSlotPlanningError as exc:
            raise WeeklyPlanningApiError(str(exc)) from exc
    else:
        result = SharedWeeklySearchResult(
            engine_version=SEARCH_ENGINE_VERSION,
            family_id=family.id,
            participant_ids=tuple(data.person_ids),
            selected_plan=None,
            evaluated_combinations=0,
            feasible_combinations=0,
            rejected_by_person_weekly_maximum=0,
            rejected_by_person_daily_limit=0,
            search_strategy="bounded",
            search_space_size=0,
            search_truncated=False,
        )

    weekly_debug(
        "SEARCH",
        "result",
        selected=result.selected_plan is not None,
        strategy=result.search_strategy,
        search_space=result.search_space_size,
        evaluated=result.evaluated_combinations,
        feasible=result.feasible_combinations,
        repeated=(
            result.selected_plan.repeated_candidate_count
            if result.selected_plan is not None
            else None
        ),
        adjacent_category_repeats=(
            result.selected_plan.adjacent_category_repeat_count
            if result.selected_plan is not None
            else None
        ),
        adjacent_protein_repeats=(
            result.selected_plan.adjacent_protein_repeat_count
            if result.selected_plan is not None
            else None
        ),
        distinct_categories=(
            result.selected_plan.distinct_main_categories
            if result.selected_plan is not None
            else None
        ),
        distinct_proteins=(
            result.selected_plan.distinct_main_proteins
            if result.selected_plan is not None
            else None
        ),
        rejected_weekly_max=result.rejected_by_person_weekly_maximum,
        rejected_daily_limit=result.rejected_by_person_daily_limit,
        truncated=result.search_truncated,
    )

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
                    transformation=(
                        evidence.as_read()
                        if (
                            evidence := transformations_by_slot[choice.slot_key].get(
                                choice.candidate.selection_key
                            )
                        )
                        is not None
                        else None
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

    read = SharedWeeklyPlanProposalRead(
        family_id=family.id,
        participant_ids=list(result.participant_ids),
        week_start=week_start,
        week_end=week_start + timedelta(days=6),
        engine_version=result.engine_version,
        slot_engine_versions=slot_engine_versions,
        selected_plan=selected_read,
        skipped_slots=skipped_slots,
        evaluated_combinations=result.evaluated_combinations,
        feasible_combinations=result.feasible_combinations,
        rejected_by_person_weekly_maximum=result.rejected_by_person_weekly_maximum,
        rejected_by_person_daily_limit=result.rejected_by_person_daily_limit,
        search_strategy=result.search_strategy,
        search_space_size=result.search_space_size,
        search_truncated=result.search_truncated,
    )
    return _ComputedWeeklyPlan(
        read=read,
        result=result,
        transformations_by_slot=transformations_by_slot,
        slots_by_key=slots_by_key,
        slot_engine_versions=slot_engine_versions,
    )



def _compute_shared_weekly_plan(
    session: Session,
    *,
    family: Family,
    data: SharedWeeklyPlanProposalCreate,
) -> _ComputedWeeklyPlan:
    with (
        weekly_debug_span(
            "WEEKLY",
            "proposal",
            family=family.id,
            slots=len(data.slots),
            people=len(data.person_ids),
        ),
        weekly_planning_cache_scope(session),
    ):
        return _compute_shared_weekly_plan_uncached(
            session,
            family=family,
            data=data,
        )

def propose_shared_weekly_plan(
    session: Session,
    *,
    family: Family,
    data: SharedWeeklyPlanProposalCreate,
) -> SharedWeeklyPlanProposalRead:
    return _compute_shared_weekly_plan(
        session,
        family=family,
        data=data,
    ).read


def _actual_transformation_ids(
    evidence: _WeeklyTransformationEvidence | None,
) -> tuple[uuid.UUID | None, uuid.UUID | None]:
    if evidence is None:
        return None, None
    return (
        evidence.proposal.operation.recipe_ingredient_id,
        evidence.proposal.operation.replacement_food_item_id,
    )


def materialize_shared_weekly_plan(
    session: Session,
    *,
    family: Family,
    data: SharedWeeklyPlanCreate,
) -> SharedWeeklyPlanRead:
    computed = _compute_shared_weekly_plan(
        session,
        family=family,
        data=data,
    )
    selected = computed.result.selected_plan
    if selected is None:
        raise WeeklyPlanningStaleError(
            "The weekly proposal is no longer feasible."
        )

    expected_by_slot = {item.slot_key: item for item in data.expected_choices}
    selected_slots = {choice.slot_key for choice in selected.choices}
    if set(expected_by_slot) != selected_slots:
        raise WeeklyPlanningStaleError(
            "The weekly proposal selection changed since preview."
        )

    for choice in selected.choices:
        expected = expected_by_slot[choice.slot_key]
        evidence = computed.transformations_by_slot[choice.slot_key].get(
            choice.candidate.selection_key
        )
        recipe_ingredient_id, replacement_food_item_id = _actual_transformation_ids(
            evidence
        )
        if (
            expected.candidate_key != choice.candidate.evaluation.candidate_key
            or expected.recipe_ingredient_id != recipe_ingredient_id
            or expected.replacement_food_item_id != replacement_food_item_id
        ):
            raise WeeklyPlanningStaleError(
                "The weekly proposal selection changed since preview."
            )

    materialized: list[SharedWeeklyPlanMaterializedChoiceRead] = []
    with session.begin_nested():
        for choice in selected.choices:
            request_slot = computed.slots_by_key[choice.slot_key]
            evidence = computed.transformations_by_slot[choice.slot_key].get(
                choice.candidate.selection_key
            )
            if evidence is not None:
                planned = materialize_selected_shared_meal_transformation(
                    session,
                    family_id=family.id,
                    recipe_id=evidence.recipe_id,
                    planning_date=choice.planning_date,
                    meal_type=choice.meal_type,
                    scheduled_at=request_slot.scheduled_at,
                    proposal=evidence.proposal,
                    title=choice.candidate.evaluation.candidate_name,
                    location=request_slot.location,
                )
                materialized.append(
                    SharedWeeklyPlanMaterializedChoiceRead(
                        slot_key=choice.slot_key,
                        meal_event_id=planned.meal_event_id,
                        candidate_key=choice.candidate.evaluation.candidate_key,
                        transformation_application_id=(
                            planned.transformation_application_id
                        ),
                        serving_ids=planned.serving_ids,
                    )
                )
                continue

            recommendation = SharedFamilyMealRecommendationResult(
                engine_version=computed.slot_engine_versions[choice.slot_key],
                evaluations=(choice.candidate.evaluation,),
            )
            planned = materialize_shared_family_recommendation(
                session,
                recommendation=recommendation,
                candidate_key=choice.candidate.evaluation.candidate_key,
                scheduled_at=request_slot.scheduled_at,
                timezone=family.timezone,
                meal_type=choice.meal_type,
                location=request_slot.location,
            )
            session.flush()
            if planned.meal_event.id is None:
                raise WeeklyPlanningApiError(
                    "A weekly MealEvent was not persisted."
                )
            serving_ids = [
                participant.serving.id
                for participant in planned.participants
                if participant.serving.id is not None
            ]
            if len(serving_ids) != len(planned.participants):
                raise WeeklyPlanningApiError(
                    "Weekly servings were not fully persisted."
                )
            materialized.append(
                SharedWeeklyPlanMaterializedChoiceRead(
                    slot_key=choice.slot_key,
                    meal_event_id=planned.meal_event.id,
                    candidate_key=choice.candidate.evaluation.candidate_key,
                    transformation_application_id=None,
                    serving_ids=serving_ids,
                )
            )


    session.commit()
    return SharedWeeklyPlanRead(
        family_id=family.id,
        status="planned",
        choices=materialized,
    )
