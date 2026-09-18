import uuid
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.family import Family
from app.models.food_catalog import FoodItem, Recipe, RecipeIngredient
from app.models.food_transformation_profile import FoodTransformationProfile
from app.models.meal import MealEvent, MealParticipant, Serving, ServingNutritionComponent
from app.models.meal_transformation_application import MealTransformationApplication
from app.models.person import Person
from app.schemas.meal_plan_fit import MealPlanFitCreate, MealPlanFitRead
from app.schemas.meal_recommendation import MealRecommendationCandidateInput
from app.schemas.meal_transformation import MealTransformationOperationRead
from app.schemas.shared_meal_transformation import (
    SharedMealTransformationBaselineRead,
    SharedMealTransformationCreate,
    SharedMealTransformationParticipantRead,
    SharedMealTransformationPlanCreate,
    SharedMealTransformationPlanRead,
    SharedMealTransformationProposalRead,
    SharedMealTransformationRead,
)
from app.services.meal_plan_fit import (
    MealPlanFitError,
    _load_daily_state,
    _load_person,
)
from app.services.meal_plan_fit_weekly_frequency import (
    apply_weekly_frequency_to_loaded_fit,
    evaluate_meal_plan_fit_with_weekly_frequency,
)
from app.services.meal_recommendation import (
    MealCandidate,
    _preference_score,
    build_recipe_candidate,
)
from app.services.meal_slot import assert_meal_slot_available
from app.services.meal_transformation import (
    SCORE_QUANTUM,
    ZERO,
    MealTransformationError,
    MealTransformationNotFoundError,
    _candidate_portion_factor,
    _evaluate_loaded_candidate,
    _latest_food_composition,
    _latest_recipe_composition,
    _profile_options,
    _replacement_quantity,
    _transformed_nutrition,
    _transformed_subjects,
)
from app.services.recipe_catalogue import RecipeNotFoundError, get_family_visible_recipe_model
from app.services.serving_nutrition import (
    NutritionSnapshot,
    UnsupportedUnitConversionError,
    scale_composition_nutrition,
)

_STATUS_RANK = {
    "fail": 0,
    "unknown": 1,
    "not_evaluated": 1,
    "support": 2,
    "pass": 3,
}


@dataclass(frozen=True)
class _ReplacementVariant:
    operation: MealTransformationOperationRead
    ingredient: RecipeIngredient
    replacement: FoodItem
    original_nutrition: NutritionSnapshot
    replacement_nutrition: NutritionSnapshot


@dataclass(frozen=True)
class _ParticipantContext:
    person: Person
    state_id: uuid.UUID | None
    quantity: Decimal
    quantity_unit: str
    baseline_fit: MealPlanFitRead
    baseline_preference_score: Decimal


def _plan_rule_score(fit: MealPlanFitRead) -> Decimal | None:
    scores = [
        result.score
        for result in fit.rule_results
        if result.source.plan_id is not None
        and result.scope in {"candidate", "meal"}
        and result.score is not None
    ]
    if not scores:
        return None
    return (sum(scores, start=ZERO) / Decimal(len(scores))).quantize(
        SCORE_QUANTUM,
        rounding=ROUND_HALF_UP,
    )


def _plan_rule_changes(
    before: MealPlanFitRead,
    after: MealPlanFitRead,
) -> tuple[list[str], list[str]]:
    before_by_id = {
        result.rule_id: result
        for result in before.rule_results
        if result.source.plan_id is not None
    }
    improved: list[str] = []
    worsened: list[str] = []
    for current in after.rule_results:
        if current.source.plan_id is None:
            continue
        previous = before_by_id.get(current.rule_id)
        if previous is None:
            continue
        previous_rank = _STATUS_RANK[previous.status]
        current_rank = _STATUS_RANK[current.status]
        if current_rank > previous_rank:
            improved.append(current.rule_id)
            continue
        if current_rank < previous_rank:
            worsened.append(current.rule_id)
            continue
        if previous.score is not None and current.score is not None:
            if current.score > previous.score:
                improved.append(current.rule_id)
            elif current.score < previous.score:
                worsened.append(current.rule_id)
    return sorted(set(improved)), sorted(set(worsened))


def _plan_score_delta(before: MealPlanFitRead, after: MealPlanFitRead) -> Decimal | None:
    before_score = _plan_rule_score(before)
    after_score = _plan_rule_score(after)
    if before_score is None or after_score is None:
        return None
    return (after_score - before_score).quantize(
        SCORE_QUANTUM,
        rounding=ROUND_HALF_UP,
    )


def _load_variants(
    db: Session,
    *,
    family_id: uuid.UUID,
    recipe: Recipe,
) -> tuple[list[_ReplacementVariant], list[str]]:
    ingredient_ids = [ingredient.food_item_id for ingredient in recipe.ingredients]
    source_profiles = list(
        db.scalars(
            select(FoodTransformationProfile)
            .options(*_profile_options())
            .where(
                FoodTransformationProfile.family_id == family_id,
                FoodTransformationProfile.food_item_id.in_(ingredient_ids),
                FoodTransformationProfile.auto_transform_enabled.is_(True),
            )
        ).all()
    )
    source_by_food = {profile.food_item_id: profile for profile in source_profiles}
    groups = sorted({profile.substitution_group for profile in source_profiles})

    alternatives: list[FoodTransformationProfile] = []
    if groups:
        alternatives = list(
            db.scalars(
                select(FoodTransformationProfile)
                .options(*_profile_options())
                .join(FoodItem, FoodItem.id == FoodTransformationProfile.food_item_id)
                .where(
                    FoodTransformationProfile.family_id == family_id,
                    FoodTransformationProfile.substitution_group.in_(groups),
                    FoodTransformationProfile.auto_transform_enabled.is_(True),
                    FoodItem.food_kind == "ingredient",
                    FoodItem.is_active.is_(True),
                    or_(FoodItem.family_id == family_id, FoodItem.family_id.is_(None)),
                )
            ).all()
        )
    alternatives_by_group: dict[str, list[FoodTransformationProfile]] = {}
    for profile in alternatives:
        alternatives_by_group.setdefault(profile.substitution_group, []).append(profile)

    variants: list[_ReplacementVariant] = []
    limitations: list[str] = []
    for ingredient in recipe.ingredients:
        source_profile = source_by_food.get(ingredient.food_item_id)
        if source_profile is None:
            continue
        original_composition = _latest_food_composition(ingredient.food_item)
        if original_composition is None:
            limitations.append(
                f"missing_source_composition:{ingredient.food_item.catalog_key}"
            )
            continue
        try:
            original_nutrition = scale_composition_nutrition(
                original_composition,
                quantity=ingredient.quantity,
                quantity_unit=ingredient.unit,
            )
        except UnsupportedUnitConversionError:
            limitations.append(
                f"unsupported_source_unit:{ingredient.food_item.catalog_key}:{ingredient.unit}"
            )
            continue

        for target_profile in alternatives_by_group.get(
            source_profile.substitution_group,
            [],
        ):
            replacement = target_profile.food_item
            if replacement.id == ingredient.food_item_id:
                continue
            replacement_composition = _latest_food_composition(replacement)
            if replacement_composition is None:
                limitations.append(
                    f"missing_replacement_composition:{replacement.catalog_key}"
                )
                continue
            try:
                replacement_quantity, replacement_unit = _replacement_quantity(
                    ingredient,
                    source_profile,
                    target_profile,
                )
                replacement_nutrition = scale_composition_nutrition(
                    replacement_composition,
                    quantity=replacement_quantity,
                    quantity_unit=replacement_unit,
                )
            except UnsupportedUnitConversionError:
                limitations.append(
                    f"insufficient_replacement_evidence:{replacement.catalog_key}"
                )
                continue
            variants.append(
                _ReplacementVariant(
                    operation=MealTransformationOperationRead(
                        substitution_group=source_profile.substitution_group,
                        recipe_ingredient_id=ingredient.id,
                        source_food_item_id=ingredient.food_item_id,
                        source_food_name=ingredient.food_item.name,
                        source_quantity=ingredient.quantity,
                        source_unit=ingredient.unit,
                        replacement_food_item_id=replacement.id,
                        replacement_food_name=replacement.name,
                        replacement_quantity=replacement_quantity,
                        replacement_unit=replacement_unit,
                    ),
                    ingredient=ingredient,
                    replacement=replacement,
                    original_nutrition=original_nutrition,
                    replacement_nutrition=replacement_nutrition,
                )
            )
    variants.sort(
        key=lambda item: (
            str(item.operation.recipe_ingredient_id),
            str(item.operation.replacement_food_item_id),
        )
    )
    return variants, sorted(set(limitations))


def _transformed_candidate(
    recipe: Recipe,
    composition,
    variant: _ReplacementVariant,
    *,
    quantity: Decimal,
    quantity_unit: str,
) -> MealCandidate:
    baseline = build_recipe_candidate(
        composition,
        quantity=quantity,
        quantity_unit=quantity_unit,
    )
    try:
        factor = _candidate_portion_factor(
            composition,
            quantity=quantity,
            quantity_unit=quantity_unit,
        )
        nutrition = _transformed_nutrition(
            baseline.nutrition,
            original=variant.original_nutrition,
            replacement=variant.replacement_nutrition,
            candidate_factor=factor,
        )
    except (UnsupportedUnitConversionError, MealTransformationError) as exc:
        raise MealTransformationError(
            f"Cannot apply replacement {variant.operation.replacement_food_name!r} safely."
        ) from exc
    return MealCandidate(
        key=recipe.recipe_key,
        name=recipe.name,
        kind="recipe",
        quantity=quantity,
        quantity_unit=quantity_unit,
        nutrition=nutrition,
        subjects=_transformed_subjects(
            recipe,
            source_ingredient_id=variant.ingredient.id,
            replacement=variant.replacement,
        ),
        recipe=recipe,
        recipe_composition=composition,
        portion_factor=factor,
    )


def _participant_contexts(
    db: Session,
    *,
    family_id: uuid.UUID,
    composition,
    data: SharedMealTransformationCreate,
) -> list[_ParticipantContext]:
    result: list[_ParticipantContext] = []
    for participant in data.participants:
        person = _load_person(db, participant.person_id)
        if person.id is None or person.family_id != family_id:
            raise MealTransformationError(
                "All shared transformation participants must belong to the requested Family."
            )
        baseline_input = MealPlanFitCreate(
            planning_date=data.planning_date,
            meal_type=data.meal_type,
            daily_nutrition_state_id=participant.daily_nutrition_state_id,
            candidate=MealRecommendationCandidateInput(
                candidate_kind="recipe",
                composition_id=composition.id,
                quantity=participant.quantity,
                quantity_unit=participant.quantity_unit,
            ),
        )
        try:
            baseline_fit = evaluate_meal_plan_fit_with_weekly_frequency(
                db,
                person_id=person.id,
                data=baseline_input,
            )
        except MealPlanFitError as exc:
            raise MealTransformationError(str(exc)) from exc
        baseline_candidate = build_recipe_candidate(
            composition,
            quantity=participant.quantity,
            quantity_unit=participant.quantity_unit,
        )
        preference_score, _ = _preference_score(
            baseline_candidate,
            list(person.food_preferences),
            data.planning_date,
        )
        result.append(
            _ParticipantContext(
                person=person,
                state_id=participant.daily_nutrition_state_id,
                quantity=participant.quantity,
                quantity_unit=participant.quantity_unit,
                baseline_fit=baseline_fit,
                baseline_preference_score=preference_score,
            )
        )
    return result


def _mean(values: list[Decimal]) -> Decimal:
    return (sum(values, start=ZERO) / Decimal(len(values))).quantize(
        SCORE_QUANTUM,
        rounding=ROUND_HALF_UP,
    )


def propose_shared_meal_transformations(
    db: Session,
    *,
    family_id: uuid.UUID,
    data: SharedMealTransformationCreate,
) -> SharedMealTransformationRead:
    try:
        recipe = get_family_visible_recipe_model(db, family_id, data.recipe_id)
    except RecipeNotFoundError as exc:
        raise MealTransformationNotFoundError(str(exc)) from exc
    composition = _latest_recipe_composition(recipe)
    if composition is None or composition.id is None:
        raise MealTransformationError(
            "Recipe has no persisted nutrition composition to transform safely."
        )

    participants = _participant_contexts(
        db,
        family_id=family_id,
        composition=composition,
        data=data,
    )
    variants, limitations = _load_variants(db, family_id=family_id, recipe=recipe)
    proposals: list[SharedMealTransformationProposalRead] = []

    for variant in variants:
        participant_results: list[SharedMealTransformationParticipantRead] = []
        unsafe = False
        any_plan_improvement = False
        for participant in participants:
            person_id = participant.person.id
            if person_id is None:
                raise MealTransformationError(
                    "Shared transformation participants must be persisted."
                )
            candidate = _transformed_candidate(
                recipe,
                composition,
                variant,
                quantity=participant.quantity,
                quantity_unit=participant.quantity_unit,
            )
            daily_state = _load_daily_state(
                db,
                person_id=person_id,
                planning_date=data.planning_date,
                state_id=participant.state_id,
            )
            base_after_fit = _evaluate_loaded_candidate(
                db,
                person=participant.person,
                candidate=candidate,
                planning_date=data.planning_date,
                meal_type=data.meal_type,
                daily_state=daily_state,
            )
            after_fit = apply_weekly_frequency_to_loaded_fit(
                db,
                person=participant.person,
                candidate=candidate,
                planning_date=data.planning_date,
                meal_type=data.meal_type,
                base_fit=base_after_fit,
            )
            improved_ids, worsened_ids = _plan_rule_changes(
                participant.baseline_fit,
                after_fit,
            )
            if not after_fit.eligible or worsened_ids:
                unsafe = True
            plan_delta = _plan_score_delta(participant.baseline_fit, after_fit)
            plan_improved = bool(improved_ids) or (
                plan_delta is not None and plan_delta > ZERO
            )
            any_plan_improvement = any_plan_improvement or plan_improved
            preference_score, _ = _preference_score(
                candidate,
                list(participant.person.food_preferences),
                data.planning_date,
            )
            preference_delta = (
                preference_score - participant.baseline_preference_score
            ).quantize(
                SCORE_QUANTUM,
                rounding=ROUND_HALF_UP,
            )
            participant_results.append(
                SharedMealTransformationParticipantRead(
                    person_id=person_id,
                    before_fit=participant.baseline_fit,
                    after_fit=after_fit,
                    plan_score_delta=plan_delta,
                    plan_improved_rule_ids=improved_ids,
                    plan_worsened_rule_ids=worsened_ids,
                    preference_delta=preference_delta,
                )
            )

        if unsafe:
            continue

        preference_deltas = [item.preference_delta for item in participant_results]
        minimum_preference_delta = min(preference_deltas)
        average_preference_delta = _mean(preference_deltas)
        preference_improvement_participants = sum(
            item.preference_delta > ZERO for item in participant_results
        )
        plan_deltas = [
            item.plan_score_delta
            for item in participant_results
            if item.plan_score_delta is not None
        ]
        minimum_plan_delta = min(plan_deltas) if plan_deltas else None
        average_plan_delta = _mean(plan_deltas) if plan_deltas else None
        plan_improvement_participants = sum(
            bool(item.plan_improved_rule_ids)
            or (item.plan_score_delta is not None and item.plan_score_delta > ZERO)
            for item in participant_results
        )

        if any_plan_improvement:
            kind = "plan_adapted"
            explanation = ["plan_backed_family_improvement"]
        elif minimum_preference_delta >= ZERO and average_preference_delta > ZERO:
            kind = "preference_variant"
            explanation = ["family_preference_improved_without_plan_claim"]
        else:
            continue

        proposals.append(
            SharedMealTransformationProposalRead(
                kind=kind,
                operation=variant.operation,
                participant_results=participant_results,
                plan_improvement_participants=plan_improvement_participants,
                preference_improvement_participants=preference_improvement_participants,
                minimum_plan_score_delta=minimum_plan_delta,
                average_plan_score_delta=average_plan_delta,
                minimum_preference_delta=minimum_preference_delta,
                average_preference_delta=average_preference_delta,
                explanation=explanation,
            )
        )

    proposals.sort(
        key=lambda item: (
            0 if item.kind == "plan_adapted" else 1,
            -item.plan_improvement_participants,
            -(item.minimum_plan_score_delta or ZERO),
            -(item.average_plan_score_delta or ZERO),
            -item.preference_improvement_participants,
            -item.minimum_preference_delta,
            -item.average_preference_delta,
            str(item.operation.recipe_ingredient_id),
            str(item.operation.replacement_food_item_id),
        )
    )

    return SharedMealTransformationRead(
        family_id=family_id,
        recipe_id=recipe.id,
        recipe_name=recipe.name,
        planning_date=data.planning_date,
        meal_type=data.meal_type,
        baseline=[
            SharedMealTransformationBaselineRead(
                person_id=participant.person.id,
                fit=participant.baseline_fit,
            )
            for participant in participants
            if participant.person.id is not None
        ],
        proposals=proposals[: data.max_proposals],
        limitations=limitations,
    )


TRANSFORMATION_APPLICATION_VERSION = "shared-meal-transformation-application-v1"


def _selected_materialization_proposal(
    result: SharedMealTransformationRead,
    data: SharedMealTransformationPlanCreate,
) -> SharedMealTransformationProposalRead:
    matches = [
        proposal
        for proposal in result.proposals
        if proposal.operation.recipe_ingredient_id == data.recipe_ingredient_id
        and proposal.operation.replacement_food_item_id == data.replacement_food_item_id
    ]
    if len(matches) != 1:
        raise MealTransformationError(
            "The selected transformation is no longer available or safe for this Family meal."
        )
    return matches[0]


def _transformation_evidence(
    proposal: SharedMealTransformationProposalRead,
) -> dict[str, object]:
    return {
        "classification": proposal.kind,
        "explanation": list(proposal.explanation),
        "plan_improvement_participants": proposal.plan_improvement_participants,
        "preference_improvement_participants": proposal.preference_improvement_participants,
        "minimum_plan_score_delta": (
            str(proposal.minimum_plan_score_delta)
            if proposal.minimum_plan_score_delta is not None
            else None
        ),
        "average_plan_score_delta": (
            str(proposal.average_plan_score_delta)
            if proposal.average_plan_score_delta is not None
            else None
        ),
        "minimum_preference_delta": str(proposal.minimum_preference_delta),
        "average_preference_delta": str(proposal.average_preference_delta),
        "participants": [
            {
                "person_id": str(participant.person_id),
                "plan_score_delta": (
                    str(participant.plan_score_delta)
                    if participant.plan_score_delta is not None
                    else None
                ),
                "plan_improved_rule_ids": list(participant.plan_improved_rule_ids),
                "plan_worsened_rule_ids": list(participant.plan_worsened_rule_ids),
                "preference_delta": str(participant.preference_delta),
                "after_fit_status": participant.after_fit.status,
                "after_fit_score": (
                    str(participant.after_fit.fit_score)
                    if participant.after_fit.fit_score is not None
                    else None
                ),
                "nutrition_plan_authority": (
                    participant.after_fit.nutrition_plan_authority.model_dump(mode="json")
                ),
            }
            for participant in proposal.participant_results
        ],
    }


def _planned_transformed_serving(
    *,
    meal_participant: MealParticipant,
    recipe: Recipe,
    participant: SharedMealTransformationParticipantRead,
    source_reference: str,
) -> Serving:
    candidate = participant.after_fit.candidate
    serving = Serving(
        meal_participant=meal_participant,
        recipe=recipe,
        item_type="recipe",
        item_key=recipe.recipe_key,
        item_name=recipe.name,
        status="planned",
        quantity_planned=candidate.quantity,
        quantity_unit=candidate.quantity_unit,
        energy_planned_kcal=candidate.nutrition.energy_kcal,
        nutrition_source="transformed",
        nutrition_calculation_version=TRANSFORMATION_APPLICATION_VERSION,
        source_reference=source_reference,
    )
    serving.nutrition_components[:] = [
        ServingNutritionComponent(
            nutrient_key=nutrient_key,
            planned_value=nutrient.value,
            served_value=None,
            consumed_value=None,
            unit=nutrient.unit,
        )
        for nutrient_key, nutrient in sorted(candidate.nutrition.nutrients.items())
    ]
    return serving


def materialize_selected_shared_meal_transformation(
    db: Session,
    *,
    family_id: uuid.UUID,
    recipe_id: uuid.UUID,
    planning_date,
    meal_type: str,
    scheduled_at,
    proposal: SharedMealTransformationProposalRead,
    title: str | None = None,
    location: str | None = None,
    notes: str | None = None,
) -> SharedMealTransformationPlanRead:
    family = db.get(Family, family_id)
    if family is None:
        raise MealTransformationNotFoundError("Family not found.")
    if scheduled_at.tzinfo is None or scheduled_at.utcoffset() is None:
        raise MealTransformationError("scheduled_at must be timezone-aware.")
    if scheduled_at.astimezone(ZoneInfo(family.timezone)).date() != planning_date:
        raise MealTransformationError(
            "planning_date must match scheduled_at in the Family timezone."
        )

    try:
        recipe = get_family_visible_recipe_model(db, family_id, recipe_id)
    except RecipeNotFoundError as exc:
        raise MealTransformationNotFoundError(str(exc)) from exc
    composition = _latest_recipe_composition(recipe)
    if composition is None or composition.id is None:
        raise MealTransformationError(
            "Recipe has no persisted nutrition composition to materialize safely."
        )

    assert_meal_slot_available(
        db,
        family_id=family_id,
        family_timezone=family.timezone,
        scheduled_at=scheduled_at,
        meal_type=meal_type,
    )

    event = MealEvent(
        family_id=family_id,
        meal_type=meal_type,
        title=title or recipe.name,
        scheduled_at=scheduled_at,
        timezone=family.timezone,
        status="planned",
        location=location,
        source="recommendation",
        source_reference=f"meal-transformation:{TRANSFORMATION_APPLICATION_VERSION}",
        notes=notes,
    )
    application = MealTransformationApplication(
        meal_event=event,
        recipe=recipe,
        source_recipe_composition_snapshot=composition,
        recipe_ingredient_id=proposal.operation.recipe_ingredient_id,
        source_food_item_id=proposal.operation.source_food_item_id,
        replacement_food_item_id=proposal.operation.replacement_food_item_id,
        sort_order=0,
        operation_type=proposal.operation.operation_type,
        transformation_kind=proposal.kind,
        substitution_group=proposal.operation.substitution_group,
        source_food_name=proposal.operation.source_food_name,
        source_quantity=proposal.operation.source_quantity,
        source_unit=proposal.operation.source_unit,
        replacement_food_name=proposal.operation.replacement_food_name,
        replacement_quantity=proposal.operation.replacement_quantity,
        replacement_unit=proposal.operation.replacement_unit,
        engine_version=TRANSFORMATION_APPLICATION_VERSION,
        evidence=_transformation_evidence(proposal),
        notes=None,
    )
    db.add(event)
    db.add(application)
    db.flush()

    source_reference = f"meal-transformation:{application.id}"
    servings: list[Serving] = []
    person_ids: list[uuid.UUID] = []
    for participant_result in proposal.participant_results:
        person = db.get(Person, participant_result.person_id)
        if person is None or person.family_id != family_id:
            raise MealTransformationError(
                "A transformation participant no longer belongs to this Family."
            )
        meal_participant = MealParticipant(
            meal_event=event,
            person=person,
            status="planned",
        )
        serving = _planned_transformed_serving(
            meal_participant=meal_participant,
            recipe=recipe,
            participant=participant_result,
            source_reference=source_reference,
        )
        db.add(meal_participant)
        db.add(serving)
        servings.append(serving)
        person_ids.append(person.id)

    db.flush()
    if event.id is None or application.id is None or any(
        serving.id is None for serving in servings
    ):
        raise MealTransformationError(
            "Shared transformation application was not fully persisted."
        )
    return SharedMealTransformationPlanRead(
        meal_event_id=event.id,
        transformation_application_id=application.id,
        status=event.status,
        transformation_kind=proposal.kind,
        recipe_id=recipe.id,
        person_ids=person_ids,
        serving_ids=[serving.id for serving in servings if serving.id is not None],
    )


def materialize_shared_meal_transformation(
    db: Session,
    *,
    family_id: uuid.UUID,
    data: SharedMealTransformationPlanCreate,
) -> SharedMealTransformationPlanRead:
    family = db.get(Family, family_id)
    if family is None:
        raise MealTransformationNotFoundError("Family not found.")
    if data.scheduled_at.tzinfo is None or data.scheduled_at.utcoffset() is None:
        raise MealTransformationError("scheduled_at must be timezone-aware.")
    if data.scheduled_at.astimezone(ZoneInfo(family.timezone)).date() != data.planning_date:
        raise MealTransformationError(
            "planning_date must match scheduled_at in the Family timezone."
        )

    result = propose_shared_meal_transformations(
        db,
        family_id=family_id,
        data=SharedMealTransformationCreate(
            planning_date=data.planning_date,
            meal_type=data.meal_type,
            recipe_id=data.recipe_id,
            participants=data.participants,
            max_proposals=10,
        ),
    )
    proposal = _selected_materialization_proposal(result, data)
    return materialize_selected_shared_meal_transformation(
        db,
        family_id=family_id,
        recipe_id=data.recipe_id,
        planning_date=data.planning_date,
        meal_type=data.meal_type,
        scheduled_at=data.scheduled_at,
        proposal=proposal,
        title=data.title,
        location=data.location,
        notes=data.notes,
    )


def plan_shared_meal_transformation(
    db: Session,
    *,
    family_id: uuid.UUID,
    data: SharedMealTransformationPlanCreate,
) -> SharedMealTransformationPlanRead:
    response = materialize_shared_meal_transformation(
        db,
        family_id=family_id,
        data=data,
    )
    db.commit()
    return response
