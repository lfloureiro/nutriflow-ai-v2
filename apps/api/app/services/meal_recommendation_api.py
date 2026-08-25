import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.daily_nutrition_state import DailyNutritionState
from app.models.food_catalog import (
    FoodCompositionSnapshot,
    Recipe,
    RecipeCompositionSnapshot,
    RecipeIngredient,
)
from app.models.meal_candidate_planning_profile import MealCandidatePlanningProfile
from app.models.person import Person
from app.schemas.meal_recommendation import (
    HumanPortionComponentRead,
    HumanPortionGuidanceRead,
    MealRecommendationCandidateInput,
    MealRecommendationCreate,
    MealRecommendationOptionRead,
    MealRecommendationRunRead,
    RecommendationNutrientRead,
    RecommendationNutritionRead,
)
from app.services.human_portion_guidance import build_human_portion_guidance
from app.services.meal_recommendation import (
    MealCandidate,
    RecommendationResult,
    build_food_candidate,
    build_recipe_candidate,
    recommend_meals,
)
from app.services.meal_suitability import (
    VALID_MEAL_TYPES,
    MealSuitabilityError,
    food_default_meal_types,
    recipe_default_meal_types,
    resolve_meal_types,
)
from app.services.recommendation_feedback import persist_recommendation_run
from app.services.serving_nutrition import UnsupportedUnitConversionError


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


def _build_food_candidate(
    composition: FoodCompositionSnapshot,
    data: MealRecommendationCandidateInput,
) -> MealCandidate:
    try:
        return build_food_candidate(
            composition,
            quantity=data.quantity,
            quantity_unit=data.quantity_unit,
        )
    except UnsupportedUnitConversionError as exc:
        raise MealRecommendationApiError(
            f"Cannot scale food candidate using quantity unit {data.quantity_unit!r}."
        ) from exc


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

    return _build_food_candidate(composition, data)


def _build_recipe_candidate(
    composition: RecipeCompositionSnapshot,
    data: MealRecommendationCandidateInput,
) -> MealCandidate:
    try:
        return build_recipe_candidate(
            composition,
            quantity=data.quantity,
            quantity_unit=data.quantity_unit,
        )
    except UnsupportedUnitConversionError as exc:
        raise MealRecommendationApiError(
            f"Cannot scale recipe candidate using quantity unit {data.quantity_unit!r}."
        ) from exc


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

    return _build_recipe_candidate(composition, data)


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


def _candidate_meal_types(
    session: Session,
    *,
    family_id: uuid.UUID,
    candidate: MealCandidate,
) -> tuple[str, ...]:
    if candidate.recipe is not None:
        profile = session.scalar(
            select(MealCandidatePlanningProfile).where(
                MealCandidatePlanningProfile.family_id == family_id,
                MealCandidatePlanningProfile.recipe_id == candidate.recipe.id,
            )
        )
        catalogue = candidate.recipe.suitable_meal_types
        defaults = recipe_default_meal_types(candidate.recipe.source)
    elif candidate.food_item is not None:
        profile = session.scalar(
            select(MealCandidatePlanningProfile).where(
                MealCandidatePlanningProfile.family_id == family_id,
                MealCandidatePlanningProfile.food_item_id == candidate.food_item.id,
            )
        )
        catalogue = candidate.food_item.suitable_meal_types
        defaults = food_default_meal_types(candidate.food_item.food_kind)
    else:
        raise MealRecommendationApiError(
            f"Candidate {candidate.key!r} has no catalogue entity."
        )
    try:
        return resolve_meal_types(
            profile=profile,
            catalogue_meal_types=catalogue,
            defaults=defaults,
        )
    except MealSuitabilityError as exc:
        raise MealRecommendationApiError(str(exc)) from exc


def _validate_candidate_meal_types(
    session: Session,
    *,
    family_id: uuid.UUID,
    meal_type: str | None,
    candidates: list[MealCandidate],
) -> None:
    if meal_type is None:
        return
    if meal_type not in VALID_MEAL_TYPES:
        raise MealRecommendationApiError(f"Unknown meal type: {meal_type!r}.")
    incompatible = [
        candidate.key
        for candidate in candidates
        if meal_type
        not in _candidate_meal_types(
            session,
            family_id=family_id,
            candidate=candidate,
        )
    ]
    if incompatible:
        raise MealRecommendationApiError(
            f"Candidates are not suitable for meal type {meal_type!r}: {incompatible!r}."
        )


def human_portion_guidance_read(
    candidate: MealCandidate,
) -> HumanPortionGuidanceRead | None:
    guidance = build_human_portion_guidance(candidate)
    if guidance is None:
        return None
    return HumanPortionGuidanceRead(
        kind=guidance.kind,
        components=[
            HumanPortionComponentRead(
                name=component.name,
                quantity=component.quantity,
                unit=component.unit,
                qualitative=component.qualitative,
            )
            for component in guidance.components
        ],
    )


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
                portion_guidance=human_portion_guidance_read(candidate),
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


def load_recommendation_inputs(
    session: Session,
    *,
    person_id: uuid.UUID,
    daily_nutrition_state_id: uuid.UUID,
    planning_date: date,
    candidates: list[MealRecommendationCandidateInput],
    meal_type: str | None = None,
) -> tuple[Person, DailyNutritionState, list[MealCandidate]]:
    person = _load_person(session, person_id)
    state = _load_daily_state(
        session,
        person=person,
        state_id=daily_nutrition_state_id,
    )
    if state.state_date != planning_date:
        raise MealRecommendationApiError(
            "planning_date must match the selected DailyNutritionState state_date."
        )
    loaded_candidates = _load_candidates(
        session,
        family_id=person.family_id,
        inputs=candidates,
    )
    _validate_candidate_meal_types(
        session,
        family_id=person.family_id,
        meal_type=meal_type,
        candidates=loaded_candidates,
    )
    return person, state, loaded_candidates


def persist_recommendation_response(
    session: Session,
    *,
    person: Person,
    state: DailyNutritionState,
    recommendation: RecommendationResult,
    planning_date: date,
    meal_type: str | None,
    context: dict[str, object] | None,
) -> MealRecommendationRunRead:
    run = persist_recommendation_run(
        session,
        person=person,
        daily_state=state,
        recommendation=recommendation,
        planning_date=planning_date,
        meal_type=meal_type,
        context=context,
    )
    session.flush()

    if run.id is None or person.id is None or state.id is None:
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
        planning_date=planning_date,
        meal_type=meal_type,
        engine_version=recommendation.engine_version,
        options=_option_response(recommendation, option_ids),
    )
    session.commit()
    return response


def create_meal_recommendation(
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
    recommendation = recommend_meals(
        daily_state=state,
        candidates=candidates,
        preferences=list(person.food_preferences),
        adverse_reactions=list(person.food_adverse_reactions),
        constraints=list(person.nutrition_constraints),
        planning_date=data.planning_date,
    )

    return persist_recommendation_response(
        session,
        person=person,
        state=state,
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
