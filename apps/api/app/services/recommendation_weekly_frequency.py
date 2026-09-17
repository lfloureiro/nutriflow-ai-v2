import uuid
from dataclasses import dataclass, replace
from datetime import date

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.meal_candidate_planning_profile import MealCandidatePlanningProfile
from app.schemas.meal_type import MealType
from app.schemas.nutrition_plan import EffectiveNutritionGuidelineRead
from app.schemas.weekly_frequency_progress import WeeklyFrequencyGuidelineProgressRead
from app.services.meal_recommendation import (
    CandidateEvaluation,
    MealCandidate,
    RecommendationResult,
)
from app.services.nutrition_plan import NutritionPlanError, compile_effective_nutrition_plan
from app.services.weekly_frequency_progress import (
    WeeklyFrequencyProgressError,
    get_weekly_frequency_progress,
)

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


class RecommendationWeeklyFrequencyError(ValueError):
    pass


@dataclass(frozen=True)
class CandidateWeeklyFrequencyImpact:
    candidate_key: str
    blocked_reasons: tuple[str, ...]
    mandatory_minimum_support: tuple[uuid.UUID, ...]
    advisory_minimum_support: tuple[uuid.UUID, ...]
    explanations: tuple[str, ...]

    @property
    def blocked(self) -> bool:
        return bool(self.blocked_reasons)


@dataclass(frozen=True)
class _CandidateProfile:
    planning_category: str | None
    primary_protein: str | None


def _normalize(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().casefold()
    return normalized or None


def _candidate_identity(candidate: MealCandidate) -> tuple[str, uuid.UUID] | None:
    if candidate.food_item is not None and candidate.food_item.id is not None:
        return "food_item", candidate.food_item.id
    if candidate.recipe is not None and candidate.recipe.id is not None:
        return "recipe", candidate.recipe.id
    return None


def _profile_map(
    db: Session,
    *,
    family_id: uuid.UUID,
    candidates: list[MealCandidate],
) -> dict[tuple[str, uuid.UUID], _CandidateProfile]:
    identities = [
        identity
        for candidate in candidates
        if (identity := _candidate_identity(candidate)) is not None
    ]
    food_ids = [identity for kind, identity in identities if kind == "food_item"]
    recipe_ids = [identity for kind, identity in identities if kind == "recipe"]
    filters = []
    if food_ids:
        filters.append(MealCandidatePlanningProfile.food_item_id.in_(food_ids))
    if recipe_ids:
        filters.append(MealCandidatePlanningProfile.recipe_id.in_(recipe_ids))
    if not filters:
        return {}

    rows = db.scalars(
        select(MealCandidatePlanningProfile).where(
            MealCandidatePlanningProfile.family_id == family_id,
            or_(*filters),
        )
    ).all()
    result: dict[tuple[str, uuid.UUID], _CandidateProfile] = {}
    for row in rows:
        if row.food_item_id is not None:
            identity = ("food_item", row.food_item_id)
        elif row.recipe_id is not None:
            identity = ("recipe", row.recipe_id)
        else:
            continue
        result[identity] = _CandidateProfile(
            planning_category=_normalize(row.planning_category),
            primary_protein=_normalize(row.primary_protein),
        )
    return result


def _candidate_match(
    candidate: MealCandidate,
    guideline: EffectiveNutritionGuidelineRead,
    *,
    profile: _CandidateProfile | None,
) -> tuple[bool | None, tuple[str, ...]]:
    target_type = _normalize(guideline.target_type)
    target_key = _normalize(guideline.target_key)
    if target_type is None or target_key is None or target_type not in _SUPPORTED_TARGET_TYPES:
        return None, ()

    if target_type == "food_item":
        if candidate.food_item is not None:
            return _normalize(candidate.food_item.catalog_key) == target_key, ("food_item",)
        if candidate.recipe is not None:
            return False, ()
        return None, ()

    if target_type == "recipe":
        if candidate.recipe is not None:
            return _normalize(candidate.recipe.recipe_key) == target_key, ("recipe",)
        if candidate.food_item is not None:
            return False, ()
        return None, ()

    if profile is None:
        return None, ()

    if target_type == "planning_category":
        if profile.planning_category is None:
            return None, ()
        return profile.planning_category == target_key, ("planning_category",)

    if target_type == "primary_protein":
        if profile.primary_protein is None:
            return None, ()
        return profile.primary_protein == target_key, ("primary_protein",)

    values = {
        key: value
        for key, value in (
            ("planning_category", profile.planning_category),
            ("primary_protein", profile.primary_protein),
        )
        if value is not None
    }
    if not values:
        return None, ()
    matched_by = tuple(sorted(key for key, value in values.items() if value == target_key))
    if matched_by:
        return True, matched_by
    return False, ()


def _active_frequency_guidelines(
    db: Session,
    *,
    person_id: uuid.UUID,
    planning_date: date,
    meal_type: MealType,
) -> list[EffectiveNutritionGuidelineRead]:
    try:
        effective = compile_effective_nutrition_plan(
            db,
            person_id=person_id,
            on_date=planning_date,
            meal_type=meal_type,
        )
    except NutritionPlanError as exc:
        raise RecommendationWeeklyFrequencyError(str(exc)) from exc
    return [
        guideline
        for guideline in effective.guidelines
        if guideline.guideline_type == "frequency" and guideline.period == "week"
    ]


def _deficit_is_confirmed(progress: WeeklyFrequencyGuidelineProgressRead) -> bool:
    if progress.minimum_occurrences is None or progress.total_occurrences is None:
        return False
    if progress.total_occurrences >= progress.minimum_occurrences:
        return False
    if not progress.counts_are_lower_bound:
        return True
    possible_total = progress.total_occurrences + (progress.unclassified_meal_count or 0)
    return possible_total < progress.minimum_occurrences


def _mandatory_max_would_be_unsafe(
    progress: WeeklyFrequencyGuidelineProgressRead,
    *,
    candidate_match: bool | None,
) -> bool:
    maximum = progress.maximum_occurrences
    total = progress.total_occurrences
    if maximum is None or total is None:
        return False
    if candidate_match is False:
        return False

    possible_existing = total
    if progress.counts_are_lower_bound:
        possible_existing += progress.unclassified_meal_count or 0
    possible_candidate_increment = 1 if candidate_match is not False else 0
    return possible_existing + possible_candidate_increment > maximum


def evaluate_candidate_weekly_frequency_impacts(
    db: Session,
    *,
    person_id: uuid.UUID,
    family_id: uuid.UUID,
    planning_date: date,
    meal_type: MealType,
    candidates: list[MealCandidate],
) -> dict[str, CandidateWeeklyFrequencyImpact]:
    guidelines = _active_frequency_guidelines(
        db,
        person_id=person_id,
        planning_date=planning_date,
        meal_type=meal_type,
    )
    if not guidelines:
        return {
            candidate.key: CandidateWeeklyFrequencyImpact(
                candidate_key=candidate.key,
                blocked_reasons=(),
                mandatory_minimum_support=(),
                advisory_minimum_support=(),
                explanations=(),
            )
            for candidate in candidates
        }

    try:
        weekly = get_weekly_frequency_progress(
            db,
            person_id=person_id,
            anchor_date=planning_date,
        )
    except WeeklyFrequencyProgressError as exc:
        raise RecommendationWeeklyFrequencyError(str(exc)) from exc

    progress_by_id = {item.guideline_id: item for item in weekly.guidelines}
    profiles = _profile_map(db, family_id=family_id, candidates=candidates)
    impacts: dict[str, CandidateWeeklyFrequencyImpact] = {}

    for candidate in candidates:
        profile_identity = _candidate_identity(candidate)
        profile = profiles.get(profile_identity) if profile_identity is not None else None
        blocked_reasons: set[str] = set()
        mandatory_support: set[uuid.UUID] = set()
        advisory_support: set[uuid.UUID] = set()
        explanations: set[str] = set()

        for guideline in guidelines:
            progress = progress_by_id.get(guideline.id)
            if progress is None:
                if guideline.is_mandatory and guideline.maximum_occurrences is not None:
                    blocked_reasons.add(
                        f"weekly_frequency_progress_missing:{guideline.id}"
                    )
                continue

            matches, matched_by = _candidate_match(
                candidate,
                guideline,
                profile=profile,
            )

            if guideline.maximum_occurrences is not None and guideline.is_mandatory:
                if progress.evidence_status != "evaluated":
                    blocked_reasons.add(
                        f"weekly_frequency_target_unsupported:{guideline.id}"
                    )
                elif _mandatory_max_would_be_unsafe(
                    progress,
                    candidate_match=matches,
                ):
                    reason = (
                        "weekly_frequency_classification_unknown"
                        if matches is None
                        else "weekly_frequency_max"
                    )
                    blocked_reasons.add(f"{reason}:{guideline.id}")

            if matches is True and _deficit_is_confirmed(progress):
                if guideline.is_mandatory:
                    mandatory_support.add(guideline.id)
                else:
                    advisory_support.add(guideline.id)
                explanations.add(
                    "weekly_frequency_support:"
                    f"{guideline.id}:"
                    f"{'+'.join(matched_by) if matched_by else 'explicit'}"
                )
            elif (
                matches is True
                and guideline.maximum_occurrences is not None
                and progress.total_occurrences is not None
                and progress.total_occurrences >= guideline.maximum_occurrences
                and not guideline.is_mandatory
            ):
                explanations.add(f"weekly_frequency_advisory_max:{guideline.id}")

        impacts[candidate.key] = CandidateWeeklyFrequencyImpact(
            candidate_key=candidate.key,
            blocked_reasons=tuple(sorted(blocked_reasons)),
            mandatory_minimum_support=tuple(sorted(mandatory_support, key=str)),
            advisory_minimum_support=tuple(sorted(advisory_support, key=str)),
            explanations=tuple(sorted(explanations)),
        )

    return impacts


def apply_weekly_frequency_to_recommendation(
    recommendation: RecommendationResult,
    *,
    impacts: dict[str, CandidateWeeklyFrequencyImpact],
) -> RecommendationResult:
    missing = {
        evaluation.candidate.key
        for evaluation in recommendation.evaluations
        if evaluation.candidate.key not in impacts
    }
    if missing:
        raise RecommendationWeeklyFrequencyError(
            "Missing weekly frequency evidence for candidates: "
            + ", ".join(sorted(missing))
            + "."
        )

    provisional: list[tuple[CandidateEvaluation, CandidateWeeklyFrequencyImpact, int]] = []
    for evaluation in recommendation.evaluations:
        impact = impacts[evaluation.candidate.key]
        original_rank = evaluation.rank if evaluation.rank is not None else 10**9
        if evaluation.eligible and impact.blocked:
            adjusted = replace(
                evaluation,
                eligible=False,
                rank=None,
                score=None,
                exclusion_reasons=tuple(
                    sorted(set(evaluation.exclusion_reasons) | set(impact.blocked_reasons))
                ),
                explanation=evaluation.explanation
                + ("Excluded by mandatory weekly frequency guidance.",)
                + impact.explanations,
            )
        else:
            adjusted = replace(
                evaluation,
                explanation=evaluation.explanation + impact.explanations,
            )
        provisional.append((adjusted, impact, original_rank))

    eligible = sorted(
        (item for item in provisional if item[0].eligible),
        key=lambda item: (
            -len(item[1].mandatory_minimum_support),
            -len(item[1].advisory_minimum_support),
            item[2],
            item[0].candidate.key,
        ),
    )
    rank_by_key = {
        evaluation.candidate.key: rank
        for rank, (evaluation, _, _) in enumerate(eligible, start=1)
    }

    adjusted_evaluations = tuple(
        replace(evaluation, rank=rank_by_key.get(evaluation.candidate.key))
        for evaluation, impact, original_rank in sorted(
            provisional,
            key=lambda item: (
                0 if item[0].eligible else 1,
                rank_by_key.get(item[0].candidate.key, 10**9),
                item[2],
                item[0].candidate.key,
            ),
        )
    )
    return RecommendationResult(
        engine_version=f"{recommendation.engine_version}+weekly-frequency-v1",
        evaluations=adjusted_evaluations,
    )
