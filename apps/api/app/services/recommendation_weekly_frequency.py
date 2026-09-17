from dataclasses import replace

from app.schemas.meal_plan_fit import MealPlanFitRead
from app.services.meal_recommendation import CandidateEvaluation, RecommendationResult


class RecommendationWeeklyFrequencyError(ValueError):
    pass


def weekly_support_counts(fit: MealPlanFitRead) -> tuple[int, int]:
    mandatory = 0
    advisory = 0
    for guideline in fit.guideline_results:
        if guideline.guideline_type != "frequency" or guideline.period != "week":
            continue
        if guideline.status != "support":
            continue
        if guideline.is_mandatory:
            mandatory += 1
        else:
            advisory += 1
    return mandatory, advisory


def apply_weekly_frequency_to_recommendation(
    recommendation: RecommendationResult,
    *,
    plan_fits: dict[str, MealPlanFitRead],
) -> RecommendationResult:
    missing = {
        evaluation.candidate.key
        for evaluation in recommendation.evaluations
        if evaluation.candidate.key not in plan_fits
    }
    if missing:
        raise RecommendationWeeklyFrequencyError(
            "Missing Plan-Fit evidence for weekly adaptation: "
            + ", ".join(sorted(missing))
            + "."
        )

    has_weekly_guidance = any(
        guideline.guideline_type == "frequency" and guideline.period == "week"
        for fit in plan_fits.values()
        for guideline in fit.guideline_results
    )
    if not has_weekly_guidance:
        return recommendation

    provisional: list[tuple[CandidateEvaluation, int, int, int]] = []
    for evaluation in recommendation.evaluations:
        mandatory_support, advisory_support = weekly_support_counts(
            plan_fits[evaluation.candidate.key]
        )
        original_rank = evaluation.rank if evaluation.rank is not None else 10**9
        explanation = evaluation.explanation
        if mandatory_support:
            explanation += (f"weekly_frequency_support:mandatory:{mandatory_support}",)
        if advisory_support:
            explanation += (f"weekly_frequency_support:advisory:{advisory_support}",)
        provisional.append(
            (
                replace(evaluation, explanation=explanation),
                mandatory_support,
                advisory_support,
                original_rank,
            )
        )

    eligible = sorted(
        (item for item in provisional if item[0].eligible),
        key=lambda item: (-item[1], -item[2], item[3], item[0].candidate.key),
    )
    rank_by_key = {
        evaluation.candidate.key: rank
        for rank, (evaluation, _, _, _) in enumerate(eligible, start=1)
    }
    adjusted = tuple(
        replace(evaluation, rank=rank_by_key.get(evaluation.candidate.key))
        for evaluation, mandatory_support, advisory_support, original_rank in sorted(
            provisional,
            key=lambda item: (
                0 if item[0].eligible else 1,
                rank_by_key.get(item[0].candidate.key, 10**9),
                item[3],
                item[0].candidate.key,
            ),
        )
    )
    return RecommendationResult(
        engine_version=f"{recommendation.engine_version}+weekly-frequency-v1",
        evaluations=adjusted,
    )