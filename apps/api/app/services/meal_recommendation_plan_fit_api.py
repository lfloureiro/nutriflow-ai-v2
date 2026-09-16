import uuid

from sqlalchemy.orm import Session

from app.schemas.meal_recommendation import MealRecommendationCreate, MealRecommendationRunRead
from app.services.meal_recommendation import recommend_meals
from app.services.meal_recommendation_api import (
    MealRecommendationApiError,
    load_recommendation_inputs,
    persist_recommendation_response,
)
from app.services.meal_recommendation_plan_fit import (
    MealRecommendationPlanFitError,
    evaluate_candidate_plan_fits,
    recommend_meals_with_plan_fit,
)


def create_meal_recommendation_with_plan_fit(
    session: Session,
    *,
    person_id: uuid.UUID,
    data: MealRecommendationCreate,
) -> MealRecommendationRunRead:
    person, state, candidates = load_recommendation_inputs(
        session,
        person_id=person_id,
        daily_nutrition_state_id=data.daily_nutrition_state_id,
        planning_date=data.planning_date,
        candidates=data.candidates,
        meal_type=data.meal_type,
    )

    if data.meal_type is None:
        # Backward-compatible unscoped calls retain the legacy evaluator until MealPlanFit
        # has an explicit no-meal-scope contract.
        recommendation = recommend_meals(
            daily_state=state,
            candidates=candidates,
            preferences=list(person.food_preferences),
            adverse_reactions=list(person.food_adverse_reactions),
            constraints=list(person.nutrition_constraints),
            planning_date=data.planning_date,
        )
        fit_mode = False
    else:
        if person.id is None or state.id is None:
            raise MealRecommendationApiError(
                "Recommendation Person and DailyNutritionState must be persisted."
            )
        try:
            plan_fits = evaluate_candidate_plan_fits(
                session,
                person_id=person.id,
                daily_nutrition_state_id=state.id,
                planning_date=data.planning_date,
                meal_type=data.meal_type,
                candidates=candidates,
            )
            recommendation = recommend_meals_with_plan_fit(
                candidates=candidates,
                plan_fits=plan_fits,
                preferences=list(person.food_preferences),
                adverse_reactions=list(person.food_adverse_reactions),
                planning_date=data.planning_date,
            )
        except MealRecommendationPlanFitError as exc:
            raise MealRecommendationApiError(str(exc)) from exc
        fit_mode = True

    return persist_recommendation_response(
        session,
        person=person,
        state=state,
        recommendation=recommendation,
        planning_date=data.planning_date,
        meal_type=data.meal_type,
        context={
            "entrypoint": "api",
            "nutrition_evaluator": "meal-plan-fit-v1" if fit_mode else "legacy-unscoped-v1",
            "candidate_composition_ids": [
                str(candidate.composition_id) for candidate in data.candidates
            ],
        },
    )
