import uuid

from sqlalchemy.orm import Session, selectinload

from app.models.daily_nutrition_state import DailyNutritionState
from app.models.food_catalog import (
    FoodCompositionSnapshot,
    Recipe,
    RecipeCompositionSnapshot,
    RecipeIngredient,
)
from app.models.person import Person
from app.schemas.meal_recommendation import (
    MealRecommendationCandidateInput,
    MealRecommendationCreate,
    MealRecommendationOptionRead,
    MealRecommendationRunRead,
    RecommendationNutritionRead,
    RecommendationNutrientRead,
)
from app.services.meal_recommendation import (
    MealCandidate,
    RecommendationResult,
    build_food_candidate,
    build_recipe_candidate,
    recommend_meals,
)
from app.services.recommendation_feedback import persist_recommendation_run


class MealRecommendationApiError(ValueError):
    pass


class MealRecommendationApiNotFoundError(MealRecommendationApiError):
    pass


def _load_person(session: Session, person_id: uuid.UUID) -> Person:
    person = session.get(
        Person,
        person_id,
        options=(
            selectinload(Person.food_preferences),
            selectinload(Person.food_adverse_reactions),
            selectinload(Person.nutrition_constraints),
        ),
    )
    if person is None:
        raise MealRecommendationApiNotFoundError("Person not found.")
    return person


def _load_daily_state(
    session: Session,
    *,
    person: Person,
    state_id: uuid.UUID,
) -> DailyNutritionState:
    state = session.get(
        DailyNutritionState,
        state_id,
        options=(selectinload(DailyNutritionState.components),),
    )
    if state is None:
        raise MealRecommendationApiNotFoundError("DailyNutritionState not found.")
    if state.person_id != person.id:
        raise MealRecommendationApiError(
            "DailyNutritionState belongs to a different Person."
        )
    return state


def _validate_catalog_family(
    *,
    family_id: uuid.UUID,
    object_family_id: uuid.UUID | None,
    candidate_key: str,
) -> None:
    if object_family_id not in {None, family_id}:
        raise MealRecommendationApiError(
            f"Candidate {candidate_key!r} belongs to another Family."
        )


def _load_food_candidate(
    session: Session,
    *,
    family_id: uuid.UUID,
    data: MealRecommendationCandidateInput,
) -> MealCandidate:
    composition = session.get(
        FoodCompositionSnapshot,
        data.composition_id,
        options=(
            selectinload(FoodCompositionSnapshot.food_item),
            selectinload(FoodCompositionSnapshot.nutrients),
        ),
    )
    if composition is None:
        raise MealRecommendationApiNotFoundError("Food composition snapshot not found.")

    food_item = composition.food_item
    _validate_catalog_family(
        family_id=family_id,
        object_family_id=food_item.family_id,
        candidate_key=food_item.catalog_key,
    )
    if not food_item.is_active:
        raise MealRecommendationApiError(
            f"Candidate {food_item.catalog_key!r} is inactive."
        )

    return build_food_candidate(
        composition,
        quantity=data.quantity,
        quantity_unit=data.quantity_unit,
    )


def _load_recipe_candidate(
    session: Session,
    *,
    family_id: uuid.UUID,
    data: MealRecommendationCandidateInput,
) -> MealCandidate:
    composition = session.get(
        RecipeCompositionSnapshot,
        data.composition_id,
        options=(
            selectinload(RecipeCompositionSnapshot.nutrients),
            selectinload(RecipeCompositionSnapshot.recipe)
            .selectinload(Recipe.ingredients)
            .selectinload(RecipeIngredient.food_item),
        ),
    )
    if composition is None:
        raise MealRecommendationApiNotFoundError("Recipe composition snapshot not found.")

    recipe = composition.recipe
    _validate_catalog_family(
        family_id=family_id,
        object_family_id=recipe.family_id,
        candidate_key=recipe.recipe_key,
    )
    if not recipe.is_active:
        raise MealRecommendationApiError(
            f"Candidate {recipe.recipe_key!r} is inactive."
        )
    for ingredient in recipe.ingredients:
        _validate_catalog_family(
            family_id=family_id,
            object_family_id=ingredient.food_item.family_id,
            candidate_key=ingredient.food_item.catalog_key,
        )

    return build_recipe_candidate(
        composition,
        quantity=data.quantity,
        quantity_unit=data.quantity_unit,
    )


def _load_candidates(
    session: Session,
    *,
    family_id: uuid.UUID,
    inputs: list[MealRecommendationCandidateInput],
) -> list[MealCandidate]:
    candidates: list[MealCandidate] = []
    for data in inputs:
        if data.candidate_kind == "food_item":
            candidate = _load_food_candidate(session, family_id=family_id, data=data)
        else:
            candidate = _load_recipe_candidate(session, family_id=family_id, data=data)
        candidates.append(candidate)

    candidate_keys = [candidate.key for candidate in candidates]
    if len(candidate_keys) != len(set(candidate_keys)):
        raise MealRecommendationApiError(
            "Recommendation candidates must have unique catalogue keys."
        )
    return candidates


def _option_response(
    recommendation: RecommendationResult,
    option_ids: list[uuid.UUID],
) -> list[MealRecommendationOptionRead]:
    if len(option_ids) != len(recommendation.evaluations):
        raise MealRecommendationApiError(
            "Persisted recommendation option count does not match the evaluation result."
        )

    responses: list[MealRecommendationOptionRead] = []
    for evaluation, option_id in zip(recommendation.evaluations, option_ids, strict=True):
        candidate = evaluation.candidate
        responses.append(
            MealRecommendationOptionRead(
                id=option_id,
                candidate_key=candidate.key,
                candidate_name=candidate.name,
                candidate_kind=candidate.kind,
                quantity=candidate.quantity,
                quantity_unit=candidate.quantity_unit,
                eligible=evaluation.eligible,
                rank=evaluation.rank,
                score=evaluation.score,
                score_breakdown=evaluation.score_breakdown,
                exclusion_reasons=list(evaluation.exclusion_reasons),
                explanation=list(evaluation.explanation),
                nutrition=RecommendationNutritionRead(
                    energy_kcal=candidate.nutrition.energy_kcal,
                    nutrients={
                        key: RecommendationNutrientRead(
                            value=nutrient.value,
                            unit=nutrient.unit,
                        )
                        for key, nutrient in sorted(candidate.nutrition.nutrients.items())
                    },
                ),
            )
        )
    return responses


def create_meal_recommendation(
    session: Session,
    *,
    person_id: uuid.UUID,
    data: MealRecommendationCreate,
) -> MealRecommendationRunRead:
    person = _load_person(session, person_id)
    state = _load_daily_state(
        session,
        person=person,
        state_id=data.daily_nutrition_state_id,
    )
    if state.state_date != data.planning_date:
        raise MealRecommendationApiError(
            "planning_date must match the selected DailyNutritionState state_date."
        )

    candidates = _load_candidates(
        session,
        family_id=person.family_id,
        inputs=data.candidates,
    )
    recommendation = recommend_meals(
        daily_state=state,
        candidates=candidates,
        preferences=list(person.food_preferences),
        adverse_reactions=list(person.food_adverse_reactions),
        constraints=list(person.nutrition_constraints),
        planning_date=data.planning_date,
    )

    run = persist_recommendation_run(
        session,
        person=person,
        daily_state=state,
        recommendation=recommendation,
        planning_date=data.planning_date,
        meal_type=data.meal_type,
        context={
            "entrypoint": "api",
            "candidate_composition_ids": [
                str(candidate.composition_id) for candidate in data.candidates
            ],
        },
    )
    session.flush()

    if run.id is None:
        raise MealRecommendationApiError("Recommendation run was not persisted.")
    option_ids: list[uuid.UUID] = []
    for option in run.options:
        if option.id is None:
            raise MealRecommendationApiError("Recommendation option was not persisted.")
        option_ids.append(option.id)

    response = MealRecommendationRunRead(
        id=run.id,
        person_id=person.id,
        daily_nutrition_state_id=state.id,
        planning_date=data.planning_date,
        meal_type=data.meal_type,
        engine_version=recommendation.engine_version,
        options=_option_response(recommendation, option_ids),
    )
    session.commit()
    return response
