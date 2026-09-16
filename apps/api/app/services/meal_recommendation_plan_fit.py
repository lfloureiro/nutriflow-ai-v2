import uuid
from datetime import date
from decimal import ROUND_HALF_UP

from sqlalchemy.orm import Session

from app.models.food_adverse_reaction import FoodAdverseReaction
from app.models.food_preference import FoodPreference
from app.schemas.meal_plan_fit import MealPlanFitCreate, MealPlanFitRead
from app.schemas.meal_recommendation import MealRecommendationCandidateInput
from app.schemas.meal_type import MealType
from app.services.meal_recommendation import (
    SCORE_QUANTUM,
    ZERO,
    CandidateEvaluation,
    MealCandidate,
    RecommendationResult,
    _advisory_reaction_score,
    _preference_score,
)


class MealRecommendationPlanFitError(ValueError):
    pass


def _candidate_input(candidate: MealCandidate) -> MealRecommendationCandidateInput:
    if candidate.food_composition is not None:
        composition_id = candidate.food_composition.id
        candidate_kind = "food_item"
    elif candidate.recipe_composition is not None:
        composition_id = candidate.recipe_composition.id
        candidate_kind = "recipe"
    else:
        raise MealRecommendationPlanFitError(
            f"Candidate {candidate.key!r} has no composition evidence for Plan-Fit."
        )

    if composition_id is None:
        raise MealRecommendationPlanFitError(
            f"Candidate {candidate.key!r} composition must be persisted before Plan-Fit."
        )

    return MealRecommendationCandidateInput(
        candidate_kind=candidate_kind,
        composition_id=composition_id,
        quantity=candidate.quantity,
        quantity_unit=candidate.quantity_unit,
    )


def evaluate_candidate_plan_fits(
    db: Session,
    *,
    person_id: uuid.UUID,
    daily_nutrition_state_id: uuid.UUID,
    planning_date: date,
    meal_type: MealType,
    candidates: list[MealCandidate],
) -> dict[str, MealPlanFitRead]:
    # Local import avoids the existing MealPlanFit -> recommendation API loader dependency
    # becoming an import cycle while that loader is still shared as technical debt.
    from app.services.meal_plan_fit import MealPlanFitError, evaluate_meal_plan_fit

    results: dict[str, MealPlanFitRead] = {}
    for candidate in candidates:
        try:
            fit = evaluate_meal_plan_fit(
                db,
                person_id=person_id,
                data=MealPlanFitCreate(
                    planning_date=planning_date,
                    meal_type=meal_type,
                    daily_nutrition_state_id=daily_nutrition_state_id,
                    candidate=_candidate_input(candidate),
                ),
            )
        except MealPlanFitError as exc:
            raise MealRecommendationPlanFitError(str(exc)) from exc

        if (
            fit.candidate.key != candidate.key
            or fit.candidate.quantity != candidate.quantity
            or fit.candidate.quantity_unit != candidate.quantity_unit
        ):
            raise MealRecommendationPlanFitError(
                f"Plan-Fit evidence does not match candidate {candidate.key!r}."
            )
        results[candidate.key] = fit
    return results


def _plan_fit_exclusion_reasons(fit: MealPlanFitRead) -> tuple[str, ...]:
    reasons: set[str] = {f"plan_fit_status:{fit.status}"}
    reasons.update(f"plan_fit_safety:{issue}" for issue in fit.safety_issues)

    for rule in fit.rule_results:
        if rule.is_mandatory and rule.status in {"fail", "unknown", "not_evaluated"}:
            reasons.add(
                "plan_fit_rule:"
                f"{rule.scope}:{rule.target_type}:{rule.target_key}:{rule.status}"
            )
    if any(conflict.severity == "mandatory" for conflict in fit.conflicts):
        reasons.add("plan_fit_conflict:mandatory")
    if any(guideline.is_mandatory for guideline in fit.guideline_results):
        reasons.add("plan_fit_guideline:mandatory:not_evaluated")
    return tuple(sorted(reasons))


def recommend_meals_with_plan_fit(
    *,
    candidates: list[MealCandidate],
    plan_fits: dict[str, MealPlanFitRead],
    preferences: list[FoodPreference],
    adverse_reactions: list[FoodAdverseReaction],
    planning_date: date,
    engine_version: str = "meal-recommendation-plan-fit-v1",
) -> RecommendationResult:
    candidate_keys = {candidate.key for candidate in candidates}
    missing = candidate_keys - set(plan_fits)
    if missing:
        raise MealRecommendationPlanFitError(
            "Missing Plan-Fit evidence for candidates: " + ", ".join(sorted(missing)) + "."
        )

    provisional: list[CandidateEvaluation] = []
    for candidate in candidates:
        fit = plan_fits[candidate.key]
        if not fit.eligible:
            provisional.append(
                CandidateEvaluation(
                    candidate=candidate,
                    eligible=False,
                    rank=None,
                    score=None,
                    score_breakdown={},
                    exclusion_reasons=_plan_fit_exclusion_reasons(fit),
                    explanation=(
                        "Excluded by Meal Plan-Fit mandatory safety or nutrition rules.",
                    ),
                )
            )
            continue

        preference_score, preference_reasons = _preference_score(
            candidate,
            preferences,
            planning_date,
        )
        reaction_score, reaction_reasons = _advisory_reaction_score(
            candidate,
            adverse_reactions,
            planning_date,
        )
        score_breakdown = {
            "preferences": preference_score,
            "advisory_reactions": reaction_score,
        }
        explanations = [f"plan_fit_status:{fit.status}"]
        if fit.fit_score is not None:
            score_breakdown["plan_fit"] = fit.fit_score
            explanations.append("plan_fit_score_available")
        else:
            # Unknown/unscored nutrition evidence is kept absent rather than coerced to zero.
            explanations.append("plan_fit_score_unavailable")

        total_score = sum(score_breakdown.values(), start=ZERO).quantize(
            SCORE_QUANTUM,
            rounding=ROUND_HALF_UP,
        )
        explanations.extend(preference_reasons)
        explanations.extend(reaction_reasons)
        provisional.append(
            CandidateEvaluation(
                candidate=candidate,
                eligible=True,
                rank=None,
                score=total_score,
                score_breakdown=score_breakdown,
                exclusion_reasons=(),
                explanation=tuple(explanations),
            )
        )

    eligible_sorted = sorted(
        (evaluation for evaluation in provisional if evaluation.eligible),
        key=lambda evaluation: (-(evaluation.score or ZERO), evaluation.candidate.key),
    )
    rank_by_key = {
        evaluation.candidate.key: rank
        for rank, evaluation in enumerate(eligible_sorted, start=1)
    }
    ranked = tuple(
        CandidateEvaluation(
            candidate=evaluation.candidate,
            eligible=evaluation.eligible,
            rank=rank_by_key.get(evaluation.candidate.key),
            score=evaluation.score,
            score_breakdown=evaluation.score_breakdown,
            exclusion_reasons=evaluation.exclusion_reasons,
            explanation=evaluation.explanation,
        )
        for evaluation in sorted(
            provisional,
            key=lambda evaluation: (
                0 if evaluation.eligible else 1,
                rank_by_key.get(evaluation.candidate.key, 10**9),
                evaluation.candidate.key,
            ),
        )
    )
    return RecommendationResult(engine_version=engine_version, evaluations=ranked)
