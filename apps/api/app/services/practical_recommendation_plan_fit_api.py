import uuid

from sqlalchemy.orm import Session

from app.schemas.practical_recommendation import (
    PracticalMealRecommendationCreate,
    PracticalMealRecommendationRunRead,
)
from app.services.commercial_availability import CommercialAvailabilityError
from app.services.meal_energy_allocation import (
    PORTION_VERSION,
    MealEnergyAllocation,
    MealEnergyAllocationError,
    size_candidates_for_meal,
)
from app.services.meal_recommendation_api import (
    load_recommendation_inputs,
    persist_recommendation_response,
)
from app.services.meal_recommendation_plan_fit import (
    MealRecommendationPlanFitError,
    evaluate_candidate_plan_fits,
)
from app.services.pantry_planning import PantryPlanningError
from app.services.persisted_practical_availability import PersistedPracticalAvailabilityError
from app.services.practical_recommendation_api import (
    PracticalRecommendationApiError,
    _allocation_context,
    _build_practical_channels,
    _commercial_offer_read,
    _merge_source_channels,
    _validate_planning_instant,
    create_practical_meal_recommendation,
)
from app.services.recipe_preference import load_family_recipe_ratings
from app.services.recommendation_diversity import apply_diversity_to_recommendation
from app.services.recommendation_feedback_learning import (
    apply_feedback_to_recommendation,
    load_person_feedback_signals,
)
from app.services.recommendation_practical_context import (
    PracticalMealContext,
    PracticalRecommendationError,
)
from app.services.recommendation_practical_plan_fit import (
    recommend_meals_with_practical_context_and_plan_fit,
)
from app.services.recommendation_weekly_frequency import (
    RecommendationWeeklyFrequencyError,
    apply_weekly_frequency_to_recommendation,
)


def create_practical_meal_recommendation_with_plan_fit(
    session: Session,
    *,
    person_id: uuid.UUID,
    data: PracticalMealRecommendationCreate,
) -> PracticalMealRecommendationRunRead:
    if data.meal_type is None:
        # MealPlanFit is explicitly meal-scoped. Keep the legacy path only for the
        # backward-compatible unscoped practical endpoint contract.
        return create_practical_meal_recommendation(session, person_id=person_id, data=data)

    person, state, candidates = load_recommendation_inputs(
        session,
        person_id=person_id,
        daily_nutrition_state_id=data.daily_nutrition_state_id,
        planning_date=data.planning_date,
        candidates=data.candidates,
        meal_type=data.meal_type,
    )
    _validate_planning_instant(data, state_timezone=state.timezone)
    if person.id is None or state.id is None:
        raise PracticalRecommendationApiError(
            "Recommendation Person and DailyNutritionState must be persisted."
        )

    feedback_signals: dict[str, object] = {}
    allocation: MealEnergyAllocation | None = None
    portion_factors: dict[str, object] = {}

    try:
        if data.auto_size_portions:
            candidates, allocation, portion_factors = size_candidates_for_meal(
                candidates,
                state,
                meal_type=data.meal_type,
            )

        plan_fits = evaluate_candidate_plan_fits(
            session,
            person_id=person.id,
            daily_nutrition_state_id=state.id,
            planning_date=data.planning_date,
            meal_type=data.meal_type,
            candidates=candidates,
        )

        channels, offers = _build_practical_channels(
            session,
            family_id=person.family_id,
            candidates=candidates,
            data=data,
        )
        practical_profiles = _merge_source_channels(candidates, channels)
        family_recipe_ratings = load_family_recipe_ratings(
            session,
            family_id=person.family_id,
            planning_date=data.planning_date,
            exclude_person_id=person.id,
        )
        has_rating_signal = bool(family_recipe_ratings) or any(
            preference.preference_type == "rating"
            for preference in person.food_preferences
        )
        base_engine_version = (
            "meal-recommendation-practical-plan-fit-v2"
            if has_rating_signal
            else "meal-recommendation-practical-plan-fit-v1"
        )
        if data.auto_size_portions:
            base_engine_version = f"{base_engine_version}+{PORTION_VERSION}"

        recommendation = recommend_meals_with_practical_context_and_plan_fit(
            candidates=candidates,
            plan_fits=plan_fits,
            preferences=list(person.food_preferences),
            adverse_reactions=list(person.food_adverse_reactions),
            planning_date=data.planning_date,
            practical_context=PracticalMealContext(
                scheduled_at=data.scheduled_at,
                location=data.location,
                available_minutes=data.available_minutes,
                has_kitchen=data.has_kitchen,
                schedule_entries=tuple(person.schedule_entries),
            ),
            practical_profiles=practical_profiles,
            family_recipe_ratings=family_recipe_ratings,
            engine_version=base_engine_version,
        )
        recommendation = apply_diversity_to_recommendation(
            session,
            family_id=person.family_id,
            planning_date=data.planning_date,
            meal_type=data.meal_type,
            recommendation=recommendation,
            provisional_history=data.provisional_history,
        )
        feedback_signals = load_person_feedback_signals(
            session,
            person_id=person.id,
            planning_date=data.planning_date,
        )
        recommendation = apply_feedback_to_recommendation(
            recommendation,
            feedback_signals=feedback_signals,
        )
        recommendation = apply_weekly_frequency_to_recommendation(
            recommendation,
            plan_fits=plan_fits,
        )
    except (
        CommercialAvailabilityError,
        MealEnergyAllocationError,
        MealRecommendationPlanFitError,
        PantryPlanningError,
        PersistedPracticalAvailabilityError,
        PracticalRecommendationError,
        RecommendationWeeklyFrequencyError,
    ) as exc:
        raise PracticalRecommendationApiError(str(exc)) from exc

    weekly_frequency_mode = recommendation.engine_version.endswith("+weekly-frequency-v1")
    source_kinds = sorted(set(data.source_kinds))
    run = persist_recommendation_response(
        session,
        person=person,
        state=state,
        recommendation=recommendation,
        planning_date=data.planning_date,
        meal_type=data.meal_type,
        context={
            "entrypoint": "practical-api",
            "nutrition_evaluator": "meal-plan-fit-v1",
            "weekly_frequency_evaluator": (
                "meal-plan-fit-weekly-frequency-v1" if weekly_frequency_mode else None
            ),
            "candidate_composition_ids": [
                str(candidate.composition_id) for candidate in data.candidates
            ],
            "scheduled_at": data.scheduled_at.isoformat(),
            "location": data.location,
            "available_minutes": data.available_minutes,
            "has_kitchen": data.has_kitchen,
            "source_kinds": source_kinds,
            "delivery_provider_keys": sorted(set(data.delivery_provider_keys)),
            "commercial_offer_keys": [offer.offer_key for offer in offers],
            "family_recipe_ratings": {
                key: str(value) for key, value in sorted(family_recipe_ratings.items())
            },
            "feedback_history": {
                key: str(value) for key, value in sorted(feedback_signals.items())
            },
            "provisional_history": [
                {"plan_date": item.plan_date.isoformat(), "candidate_key": item.candidate_key}
                for item in data.provisional_history
            ],
            "auto_size_portions": data.auto_size_portions,
            "meal_energy_allocation": _allocation_context(allocation, portion_factors),
            "max_results": data.max_results,
        },
    )

    options = run.options
    if data.max_results is not None:
        options = [option for option in options if option.eligible][: data.max_results]

    return PracticalMealRecommendationRunRead(
        id=run.id,
        person_id=run.person_id,
        daily_nutrition_state_id=run.daily_nutrition_state_id,
        planning_date=run.planning_date,
        meal_type=run.meal_type,
        engine_version=run.engine_version,
        scheduled_at=data.scheduled_at,
        location=data.location,
        source_kinds=source_kinds,
        options=options,
        commercial_offers=[_commercial_offer_read(offer) for offer in offers],
    )