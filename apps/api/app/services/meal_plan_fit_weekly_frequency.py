import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.meal_candidate_planning_profile import MealCandidatePlanningProfile
from app.models.person import Person
from app.schemas.meal_plan_fit import (
    MealPlanFitCreate,
    MealPlanFitGuidelineRead,
    MealPlanFitRead,
)
from app.schemas.meal_type import MealType
from app.schemas.nutrition_plan import EffectiveNutritionGuidelineRead
from app.schemas.weekly_frequency_progress import WeeklyFrequencyGuidelineProgressRead
from app.services.meal_plan_fit import MealPlanFitError, evaluate_meal_plan_fit
from app.services.meal_recommendation import MealCandidate
from app.services.meal_recommendation_api import _load_candidates
from app.services.nutrition_plan import NutritionPlanError, compile_effective_nutrition_plan
from app.services.weekly_frequency_progress import (
    WeeklyFrequencyProgressError,
    get_weekly_frequency_progress,
)
from app.services.weekly_planning_request_cache import current_weekly_planning_cache

_SUPPORTED_TARGET_TYPES = frozenset(
    {
        "food_category",
        "food_group",
        "planning_category",
        "primary_protein",
        "food_item",
        "recipe",
    }
)


class MealPlanFitWeeklyFrequencyError(MealPlanFitError):
    pass


def _normalize(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().casefold()
    return normalized or None


def _candidate_profile(
    db: Session,
    *,
    family_id: uuid.UUID,
    candidate: MealCandidate,
) -> MealCandidatePlanningProfile | None:
    kind: str | None = None
    candidate_id: uuid.UUID | None = None
    if candidate.food_item is not None and candidate.food_item.id is not None:
        kind = "food_item"
        candidate_id = candidate.food_item.id
    elif candidate.recipe is not None and candidate.recipe.id is not None:
        kind = "recipe"
        candidate_id = candidate.recipe.id
    if kind is None or candidate_id is None:
        return None

    cache = current_weekly_planning_cache(db)
    cache_key = (family_id, kind, candidate_id)
    if cache is not None and cache_key in cache.candidate_profiles:
        return cache.candidate_profiles[cache_key]

    if kind == "food_item":
        profile = db.scalar(
            select(MealCandidatePlanningProfile).where(
                MealCandidatePlanningProfile.family_id == family_id,
                MealCandidatePlanningProfile.food_item_id == candidate_id,
            )
        )
    else:
        profile = db.scalar(
            select(MealCandidatePlanningProfile).where(
                MealCandidatePlanningProfile.family_id == family_id,
                MealCandidatePlanningProfile.recipe_id == candidate_id,
            )
        )
    if cache is not None:
        cache.candidate_profiles[cache_key] = profile
    return profile


def _candidate_match(
    candidate: MealCandidate,
    guideline: EffectiveNutritionGuidelineRead,
    *,
    profile: MealCandidatePlanningProfile | None,
) -> tuple[bool | None, list[str]]:
    target_type = _normalize(guideline.target_type)
    target_key = _normalize(guideline.target_key)
    if target_type is None or target_key is None or target_type not in _SUPPORTED_TARGET_TYPES:
        return None, []

    if target_type == "food_item":
        if candidate.food_item is not None:
            return _normalize(candidate.food_item.catalog_key) == target_key, ["food_item"]
        if candidate.recipe is not None:
            return False, []
        return None, []

    if target_type == "recipe":
        if candidate.recipe is not None:
            return _normalize(candidate.recipe.recipe_key) == target_key, ["recipe"]
        if candidate.food_item is not None:
            return False, []
        return None, []

    if profile is None:
        return None, []

    planning_category = _normalize(profile.planning_category)
    primary_protein = _normalize(profile.primary_protein)
    if target_type == "planning_category":
        if planning_category is None:
            return None, []
        return planning_category == target_key, ["planning_category"]
    if target_type == "primary_protein":
        if primary_protein is None:
            return None, []
        return primary_protein == target_key, ["primary_protein"]

    values = {
        key: value
        for key, value in (
            ("planning_category", planning_category),
            ("primary_protein", primary_protein),
        )
        if value is not None
    }
    if not values:
        return None, []
    matched_by = sorted(key for key, value in values.items() if value == target_key)
    if matched_by:
        return True, matched_by
    return False, []


def _confirmed_minimum_deficit(progress: WeeklyFrequencyGuidelineProgressRead) -> bool:
    minimum = progress.minimum_occurrences
    total = progress.total_occurrences
    if minimum is None or total is None or total >= minimum:
        return False
    if not progress.counts_are_lower_bound:
        return True
    possible_total = total + (progress.unclassified_meal_count or 0)
    return possible_total < minimum


def _max_status(
    progress: WeeklyFrequencyGuidelineProgressRead,
    *,
    matches: bool | None,
) -> tuple[str | None, str | None]:
    maximum = progress.maximum_occurrences
    total = progress.total_occurrences
    if maximum is None:
        return None, None
    if total is None:
        return "unknown", "Weekly maximum has no evaluated occurrence total."
    if matches is False:
        return None, None

    guaranteed_projected = total + (1 if matches is True else 0)
    if matches is True and guaranteed_projected > maximum:
        return "fail", "Candidate would exceed the weekly maximum."

    possible_existing = total + (
        (progress.unclassified_meal_count or 0) if progress.counts_are_lower_bound else 0
    )
    possible_projected = possible_existing + 1
    if matches is None and total + 1 > maximum:
        return "unknown", "Candidate classification is unknown and may exceed the weekly maximum."
    if progress.counts_are_lower_bound and possible_projected > maximum:
        return "unknown", (
            "Unclassified meals mean the remaining weekly maximum capacity cannot be proven safely."
        )
    return None, None


def _frequency_result(
    guideline: EffectiveNutritionGuidelineRead,
    *,
    progress: WeeklyFrequencyGuidelineProgressRead | None,
    candidate: MealCandidate,
    profile: MealCandidatePlanningProfile | None,
) -> MealPlanFitGuidelineRead:
    base = {
        "guideline_id": guideline.id,
        "guideline_type": guideline.guideline_type,
        "target_type": guideline.target_type,
        "target_key": guideline.target_key,
        "description": guideline.description,
        "meal_type": guideline.meal_type,
        "period": guideline.period,
        "minimum_occurrences": guideline.minimum_occurrences,
        "maximum_occurrences": guideline.maximum_occurrences,
        "is_mandatory": guideline.is_mandatory,
        "priority": guideline.priority,
        "source": guideline.source,
    }
    if progress is None:
        return MealPlanFitGuidelineRead(
            **base,
            status="unknown",
            explanation="Weekly frequency progress evidence is missing for this guideline.",
        )
    if progress.evidence_status != "evaluated":
        return MealPlanFitGuidelineRead(
            **base,
            counts_are_lower_bound=progress.counts_are_lower_bound,
            unclassified_meal_count=progress.unclassified_meal_count,
            status="unknown",
            explanation="Weekly frequency target cannot be evaluated from supported structured evidence.",
        )

    matches, matched_by = _candidate_match(candidate, guideline, profile=profile)
    total = progress.total_occurrences
    projected = None if total is None else total + (1 if matches is True else 0)
    common = {
        **base,
        "current_occurrences": total,
        "projected_occurrences": projected,
        "counts_are_lower_bound": progress.counts_are_lower_bound,
        "unclassified_meal_count": progress.unclassified_meal_count,
        "candidate_matches": matches,
        "matched_by": matched_by,
    }

    max_status, max_explanation = _max_status(progress, matches=matches)
    if max_status is not None:
        return MealPlanFitGuidelineRead(
            **common,
            status=max_status,
            explanation=max_explanation or "Weekly maximum cannot be evaluated safely.",
        )

    if matches is True and _confirmed_minimum_deficit(progress):
        return MealPlanFitGuidelineRead(
            **common,
            status="support",
            explanation="Candidate contributes to a confirmed remaining weekly minimum.",
        )
    if matches is None:
        return MealPlanFitGuidelineRead(
            **common,
            status="neutral",
            explanation=(
                "Candidate classification is incomplete, but current evidence does not make it unsafe "
                "against a mandatory weekly maximum."
            ),
        )
    if matches is False:
        return MealPlanFitGuidelineRead(
            **common,
            status="neutral",
            explanation="Candidate does not contribute to this weekly frequency target.",
        )
    return MealPlanFitGuidelineRead(
        **common,
        status="pass",
        explanation="Candidate remains compatible with the current weekly frequency progress.",
    )


def _qualitative_result(guideline: EffectiveNutritionGuidelineRead) -> MealPlanFitGuidelineRead:
    return MealPlanFitGuidelineRead(
        guideline_id=guideline.id,
        guideline_type=guideline.guideline_type,
        target_type=guideline.target_type,
        target_key=guideline.target_key,
        description=guideline.description,
        meal_type=guideline.meal_type,
        period=guideline.period,
        minimum_occurrences=guideline.minimum_occurrences,
        maximum_occurrences=guideline.maximum_occurrences,
        is_mandatory=guideline.is_mandatory,
        priority=guideline.priority,
        status="not_evaluated",
        explanation="Qualitative guidance is preserved for explanation but is not scored automatically.",
        source=guideline.source,
    )


def _recompute_fit(
    base_fit: MealPlanFitRead,
    *,
    guideline_results: list[MealPlanFitGuidelineRead],
) -> MealPlanFitRead:
    mandatory_conflict = any(
        conflict.severity == "mandatory" for conflict in base_fit.conflicts
    )
    mandatory_fail = any(
        result.is_mandatory and result.status == "fail" for result in base_fit.rule_results
    ) or any(
        result.is_mandatory and result.status == "fail" for result in guideline_results
    )
    mandatory_unknown = any(
        result.is_mandatory and result.status in {"unknown", "not_evaluated"}
        for result in base_fit.rule_results
    ) or any(
        result.is_mandatory and result.status in {"unknown", "not_evaluated"}
        for result in guideline_results
    )

    eligible = not (
        base_fit.safety_issues or mandatory_conflict or mandatory_fail or mandatory_unknown
    )
    if mandatory_conflict:
        status = "conflict"
    elif base_fit.safety_issues or mandatory_fail:
        status = "fail"
    elif mandatory_unknown or base_fit.fit_score is None:
        status = "unknown"
    elif base_fit.fit_score == 1 and not any(
        result.status in {"fail", "unknown"}
        for result in base_fit.rule_results
        if result.scope in {"candidate", "meal"}
    ):
        status = "pass"
    else:
        status = "partial"

    explanation = [
        text
        for text in base_fit.explanation
        if text
        not in {
            "At least one mandatory rule cannot be evaluated safely with the available evidence/context.",
            "Qualitative and weekly-frequency guidelines are displayed but not included in fit_score v1.",
        }
    ]
    if mandatory_unknown:
        explanation.append(
            "At least one mandatory rule or guideline cannot be evaluated safely with the available evidence/context."
        )
    if any(result.guideline_type == "frequency" for result in guideline_results):
        explanation.append(
            "Weekly-frequency guidance is evaluated against Person-specific weekly progress and explicit planning metadata."
        )
    if any(result.guideline_type == "qualitative" for result in guideline_results):
        explanation.append(
            "Qualitative guidance remains visible but is not automatically inferred or scored."
        )

    return base_fit.model_copy(
        update={
            "eligible": eligible,
            "status": status,
            "guideline_results": guideline_results,
            "explanation": explanation,
        }
    )


def apply_weekly_frequency_to_loaded_fit(
    db: Session,
    *,
    person: Person,
    candidate: MealCandidate,
    planning_date: date,
    meal_type: MealType,
    base_fit: MealPlanFitRead,
) -> MealPlanFitRead:
    if person.id is None or person.family_id is None:
        raise MealPlanFitWeeklyFrequencyError(
            "Weekly Plan-Fit requires a persisted Person and Family."
        )
    if base_fit.person_id != person.id:
        raise MealPlanFitWeeklyFrequencyError(
            "Base Plan-Fit belongs to a different Person."
        )
    if base_fit.planning_date != planning_date or base_fit.meal_type != meal_type:
        raise MealPlanFitWeeklyFrequencyError(
            "Base Plan-Fit belongs to a different planning slot."
        )
    if base_fit.candidate.key != candidate.key:
        raise MealPlanFitWeeklyFrequencyError(
            "Base Plan-Fit evidence does not match the loaded candidate."
        )

    profile = _candidate_profile(
        db,
        family_id=person.family_id,
        candidate=candidate,
    )
    cache = current_weekly_planning_cache(db)
    effective_key = (person.id, planning_date, meal_type)
    weekly_key = (person.id, planning_date)
    try:
        effective = (
            cache.effective_plans.get(effective_key)
            if cache is not None
            else None
        )
        if effective is None:
            effective = compile_effective_nutrition_plan(
                db,
                person_id=person.id,
                on_date=planning_date,
                meal_type=meal_type,
            )
            if cache is not None:
                cache.effective_plans[effective_key] = effective

        weekly = (
            cache.weekly_progress.get(weekly_key)
            if cache is not None
            else None
        )
        if weekly is None:
            weekly = get_weekly_frequency_progress(
                db,
                person_id=person.id,
                anchor_date=planning_date,
            )
            if cache is not None:
                cache.weekly_progress[weekly_key] = weekly
    except (NutritionPlanError, WeeklyFrequencyProgressError) as exc:
        raise MealPlanFitWeeklyFrequencyError(str(exc)) from exc

    progress_by_id = {item.guideline_id: item for item in weekly.guidelines}
    results: list[MealPlanFitGuidelineRead] = []
    for guideline in effective.guidelines:
        if guideline.guideline_type == "frequency" and guideline.period == "week":
            results.append(
                _frequency_result(
                    guideline,
                    progress=progress_by_id.get(guideline.id),
                    candidate=candidate,
                    profile=profile,
                )
            )
        else:
            results.append(_qualitative_result(guideline))
    return _recompute_fit(base_fit, guideline_results=results)


def evaluate_meal_plan_fit_with_weekly_frequency(
    db: Session,
    *,
    person_id: uuid.UUID,
    data: MealPlanFitCreate,
) -> MealPlanFitRead:
    base_fit = evaluate_meal_plan_fit(db, person_id=person_id, data=data)
    person = db.get(Person, person_id)
    if person is None:
        raise MealPlanFitWeeklyFrequencyError("Person not found.")
    candidates = _load_candidates(
        db,
        family_id=person.family_id,
        inputs=[data.candidate],
    )
    candidate = candidates[0]
    return apply_weekly_frequency_to_loaded_fit(
        db,
        person=person,
        candidate=candidate,
        planning_date=data.planning_date,
        meal_type=data.meal_type,
        base_fit=base_fit,
    )
