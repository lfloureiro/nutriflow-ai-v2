from datetime import date
from decimal import Decimal

from app.models.food_adverse_reaction import FoodAdverseReaction
from app.models.food_preference import FoodPreference
from app.schemas.meal_plan_fit import MealPlanFitRead
from app.services.meal_recommendation import (
    CandidateEvaluation,
    MealCandidate,
    RecommendationResult,
)
from app.services.meal_recommendation_plan_fit import recommend_meals_with_plan_fit
from app.services.recommendation_practical_context import (
    CandidatePracticalProfile,
    PracticalMealContext,
    _practical_exclusions,
    _practical_explanations,
    _profile_map,
    _rerank_with_family_preferences,
    evaluate_schedule_context,
)


def recommend_meals_with_practical_context_and_plan_fit(
    *,
    candidates: list[MealCandidate],
    plan_fits: dict[str, MealPlanFitRead],
    preferences: list[FoodPreference],
    adverse_reactions: list[FoodAdverseReaction],
    planning_date: date,
    practical_context: PracticalMealContext,
    practical_profiles: tuple[CandidatePracticalProfile, ...] = (),
    family_recipe_ratings: dict[str, Decimal] | None = None,
    engine_version: str = "meal-recommendation-practical-plan-fit-v1",
) -> RecommendationResult:
    schedule = evaluate_schedule_context(practical_context)
    profiles = _profile_map(practical_profiles)

    practical_excluded: list[CandidateEvaluation] = []
    practical_candidates: list[MealCandidate] = []
    for candidate in candidates:
        exclusions = _practical_exclusions(
            profiles.get(candidate.key),
            practical_context,
            schedule,
        )
        if exclusions:
            practical_excluded.append(
                CandidateEvaluation(
                    candidate=candidate,
                    eligible=False,
                    rank=None,
                    score=None,
                    score_breakdown={},
                    exclusion_reasons=exclusions,
                    explanation=("Excluded by practical planning context.",),
                )
            )
        else:
            practical_candidates.append(candidate)

    practical_keys = {candidate.key for candidate in practical_candidates}
    base_result = recommend_meals_with_plan_fit(
        candidates=practical_candidates,
        plan_fits={key: fit for key, fit in plan_fits.items() if key in practical_keys},
        preferences=preferences,
        adverse_reactions=adverse_reactions,
        planning_date=planning_date,
        engine_version=engine_version,
    )
    evaluated = _rerank_with_family_preferences(
        base_result,
        family_recipe_ratings or {},
        _practical_explanations(practical_context, schedule),
    )
    evaluated.extend(practical_excluded)
    evaluated.sort(
        key=lambda evaluation: (
            0 if evaluation.eligible else 1,
            evaluation.rank if evaluation.rank is not None else 10**9,
            evaluation.candidate.key,
        )
    )
    return RecommendationResult(engine_version=engine_version, evaluations=tuple(evaluated))
