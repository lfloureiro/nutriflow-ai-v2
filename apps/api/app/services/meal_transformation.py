import uuid
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.daily_nutrition_state import DailyNutritionState
from app.models.food_catalog import FoodCompositionSnapshot, FoodItem, Recipe, RecipeIngredient
from app.models.food_transformation_profile import FoodTransformationProfile
from app.models.person import Person
from app.schemas.meal_plan_fit import (
    MealPlanFitCreate,
    MealPlanFitGuidelineRead,
    MealPlanFitRead,
)
from app.schemas.meal_recommendation import MealRecommendationCandidateInput
from app.schemas.meal_transformation import (
    MealTransformationCreate,
    MealTransformationOperationRead,
    MealTransformationProposalRead,
    MealTransformationRead,
)
from app.schemas.nutrition_plan import EffectiveNutritionPlanRead
from app.services.meal_plan_fit import (
    ONE,
    SCORE_QUANTUM,
    ZERO,
    MealPlanFitError,
    _candidate_read,
    _evaluate_rule,
    _load_daily_state,
    _load_person,
    _mandatory_reaction_issues,
    evaluate_meal_plan_fit,
)
from app.services.meal_recommendation import MealCandidate, build_recipe_candidate
from app.services.nutrition_plan import NutritionPlanError, compile_effective_nutrition_plan
from app.services.recipe_catalogue import RecipeNotFoundError, get_family_visible_recipe_model
from app.services.serving_nutrition import (
    NutrientSnapshot,
    NutritionSnapshot,
    UnsupportedUnitConversionError,
    convert_quantity,
    scale_composition_nutrition,
)


class MealTransformationError(ValueError):
    pass


class MealTransformationNotFoundError(MealTransformationError):
    pass


def _latest_food_composition(item: FoodItem) -> FoodCompositionSnapshot | None:
    return item.compositions[-1] if item.compositions else None


def _latest_recipe_composition(recipe: Recipe):
    return recipe.compositions[-1] if recipe.compositions else None


def _food_subjects(item: FoodItem) -> set[tuple[str, str]]:
    return {
        ("food", item.catalog_key),
        ("food_item", item.catalog_key),
        (item.food_kind, item.catalog_key),
    }


def _transformed_subjects(
    recipe: Recipe,
    *,
    source_ingredient_id: uuid.UUID,
    replacement: FoodItem,
) -> frozenset[tuple[str, str]]:
    subjects: set[tuple[str, str]] = {("recipe", recipe.recipe_key)}
    for ingredient in recipe.ingredients:
        item = replacement if ingredient.id == source_ingredient_id else ingredient.food_item
        subjects.update(_food_subjects(item))
    return frozenset(subjects)


def _replacement_quantity(
    ingredient: RecipeIngredient,
    source_profile: FoodTransformationProfile,
    target_profile: FoodTransformationProfile,
) -> tuple[Decimal, str]:
    if (
        source_profile.typical_quantity is not None
        and source_profile.typical_unit is not None
        and target_profile.typical_quantity is not None
        and target_profile.typical_unit is not None
    ):
        source_quantity = convert_quantity(
            ingredient.quantity,
            ingredient.unit,
            source_profile.typical_unit,
        )
        equivalents = source_quantity / source_profile.typical_quantity
        return target_profile.typical_quantity * equivalents, target_profile.typical_unit
    return ingredient.quantity, ingredient.unit


def _candidate_portion_factor(
    recipe_composition,
    *,
    quantity: Decimal,
    quantity_unit: str,
) -> Decimal:
    reference_quantity = convert_quantity(
        quantity,
        quantity_unit,
        recipe_composition.reference_unit,
    )
    return reference_quantity / recipe_composition.reference_quantity


def _transformed_nutrition(
    baseline: NutritionSnapshot,
    *,
    original: NutritionSnapshot,
    replacement: NutritionSnapshot,
    candidate_factor: Decimal,
) -> NutritionSnapshot:
    if (
        baseline.energy_kcal is not None
        and original.energy_kcal is not None
        and replacement.energy_kcal is not None
    ):
        energy = baseline.energy_kcal + (
            replacement.energy_kcal - original.energy_kcal
        ) * candidate_factor
        energy = max(ZERO, energy)
    else:
        energy = baseline.energy_kcal

    nutrients: dict[str, NutrientSnapshot] = {}
    for key, baseline_nutrient in baseline.nutrients.items():
        original_nutrient = original.nutrients.get(key)
        replacement_nutrient = replacement.nutrients.get(key)
        if original_nutrient is None or replacement_nutrient is None:
            raise MealTransformationError(
                f"Replacement evidence is incomplete for nutrient {key!r}."
            )
        original_value = convert_quantity(
            original_nutrient.value,
            original_nutrient.unit,
            baseline_nutrient.unit,
        )
        replacement_value = convert_quantity(
            replacement_nutrient.value,
            replacement_nutrient.unit,
            baseline_nutrient.unit,
        )
        value = baseline_nutrient.value + (
            replacement_value - original_value
        ) * candidate_factor
        nutrients[key] = NutrientSnapshot(
            value=max(ZERO, value),
            unit=baseline_nutrient.unit,
        )
    return NutritionSnapshot(energy_kcal=energy, nutrients=nutrients)


def _evaluate_loaded_candidate(
    db: Session,
    *,
    person: Person,
    candidate: MealCandidate,
    planning_date: date,
    meal_type: str,
    daily_state: DailyNutritionState | None,
) -> MealPlanFitRead:
    try:
        effective_plan: EffectiveNutritionPlanRead = compile_effective_nutrition_plan(
            db,
            person_id=person.id,
            on_date=planning_date,
            meal_type=meal_type,
        )
    except NutritionPlanError as exc:
        raise MealTransformationError(str(exc)) from exc

    safety_issues = _mandatory_reaction_issues(
        list(person.food_adverse_reactions),
        candidate=candidate,
        planning_date=planning_date,
    )
    rule_results = [
        _evaluate_rule(rule, candidate=candidate, daily_state=daily_state)
        for rule in effective_plan.numeric_rules
    ]
    guideline_results = [
        MealPlanFitGuidelineRead(
            guideline_id=guideline.id,
            description=guideline.description,
            is_mandatory=guideline.is_mandatory,
            priority=guideline.priority,
            explanation=(
                "Weekly frequency progress is not evaluated in Plan-Fit v1."
                if guideline.guideline_type == "frequency"
                else "Qualitative guidance is preserved for explanation but is not scored in Plan-Fit v1."
            ),
            source=guideline.source,
        )
        for guideline in effective_plan.guidelines
    ]

    mandatory_conflict = any(
        conflict.severity == "mandatory" for conflict in effective_plan.conflicts
    )
    mandatory_fail = any(
        result.is_mandatory and result.status == "fail" for result in rule_results
    )
    mandatory_unknown = any(
        result.is_mandatory and result.status in {"unknown", "not_evaluated"}
        for result in rule_results
    ) or any(guideline.is_mandatory for guideline in guideline_results)

    scored = [
        result.score
        for result in rule_results
        if result.scope in {"candidate", "meal"} and result.score is not None
    ]
    fit_score = (
        (sum(scored, start=ZERO) / Decimal(len(scored))).quantize(
            SCORE_QUANTUM,
            rounding=ROUND_HALF_UP,
        )
        if scored
        else None
    )

    eligible = not (
        safety_issues or mandatory_conflict or mandatory_fail or mandatory_unknown
    )
    if mandatory_conflict:
        status = "conflict"
    elif safety_issues or mandatory_fail:
        status = "fail"
    elif mandatory_unknown or fit_score is None:
        status = "unknown"
    elif fit_score == ONE and not any(
        result.status in {"fail", "unknown"}
        for result in rule_results
        if result.scope in {"candidate", "meal"}
    ):
        status = "pass"
    else:
        status = "partial"

    explanation: list[str] = []
    if not effective_plan.active_plans:
        explanation.append(
            "No active NutritionPlan applies; standalone Person targets and constraints may still be shown."
        )
    if safety_issues:
        explanation.append("Candidate is blocked by a mandatory adverse-reaction rule.")
    if mandatory_conflict:
        explanation.append("The effective plan contains conflicting mandatory numeric guidance.")
    if mandatory_unknown:
        explanation.append(
            "At least one mandatory rule cannot be evaluated safely with the available evidence/context."
        )
    if fit_score is not None:
        explanation.append(
            "fit_score is the mean satisfaction score of candidate-level and meal-scoped numeric rules only."
        )
    if guideline_results:
        explanation.append(
            "Qualitative and weekly-frequency guidelines are displayed but not included in fit_score v1."
        )

    return MealPlanFitRead(
        person_id=person.id,
        planning_date=planning_date,
        meal_type=meal_type,
        daily_nutrition_state_id=daily_state.id if daily_state is not None else None,
        candidate=_candidate_read(candidate),
        eligible=eligible,
        status=status,
        fit_score=fit_score,
        active_plans=effective_plan.active_plans,
        conflicts=effective_plan.conflicts,
        safety_issues=safety_issues,
        rule_results=rule_results,
        guideline_results=guideline_results,
        explanation=explanation,
    )


def _fit_delta(before: MealPlanFitRead, after: MealPlanFitRead) -> Decimal | None:
    if before.fit_score is None or after.fit_score is None:
        return None
    return (after.fit_score - before.fit_score).quantize(
        SCORE_QUANTUM,
        rounding=ROUND_HALF_UP,
    )


def _daily_improvement(before: MealPlanFitRead, after: MealPlanFitRead) -> bool:
    rank = {"fail": 0, "unknown": 0, "not_evaluated": 0, "support": 1, "pass": 2}
    before_by_id = {item.rule_id: item for item in before.rule_results if item.scope == "daily"}
    for item in after.rule_results:
        if item.scope != "daily":
            continue
        previous = before_by_id.get(item.rule_id)
        if previous is not None and rank[item.status] > rank[previous.status]:
            return True
    return False


def _changed_rule_ids(before: MealPlanFitRead, after: MealPlanFitRead) -> list[str]:
    before_by_id = {item.rule_id: item for item in before.rule_results}
    changed: list[str] = []
    for item in after.rule_results:
        previous = before_by_id.get(item.rule_id)
        if previous is None:
            changed.append(item.rule_id)
            continue
        if (
            previous.status != item.status
            or previous.observed_value != item.observed_value
            or previous.projected_daily_value != item.projected_daily_value
        ):
            changed.append(item.rule_id)
    return changed


def _is_improvement(before: MealPlanFitRead, after: MealPlanFitRead) -> bool:
    if after.eligible and not before.eligible:
        return True
    delta = _fit_delta(before, after)
    if delta is not None and delta > ZERO:
        return True
    return _daily_improvement(before, after)


def _proposal_explanation(before: MealPlanFitRead, after: MealPlanFitRead) -> list[str]:
    result: list[str] = []
    if after.eligible and not before.eligible:
        result.append("mandatory_block_resolved")
    delta = _fit_delta(before, after)
    if delta is not None and delta > ZERO:
        result.append("meal_fit_improved")
    if _daily_improvement(before, after):
        result.append("daily_target_progress_improved")
    return result


def _profile_options():
    return (
        selectinload(FoodTransformationProfile.food_item)
        .selectinload(FoodItem.compositions)
        .selectinload(FoodCompositionSnapshot.nutrients),
    )


def propose_meal_transformations(
    db: Session,
    *,
    person_id: uuid.UUID,
    data: MealTransformationCreate,
) -> MealTransformationRead:
    person = _load_person(db, person_id)
    try:
        recipe = get_family_visible_recipe_model(db, person.family_id, data.recipe_id)
    except RecipeNotFoundError as exc:
        raise MealTransformationNotFoundError(str(exc)) from exc

    composition = _latest_recipe_composition(recipe)
    if composition is None:
        raise MealTransformationError("Recipe has no nutrition composition to transform safely.")

    baseline_input = MealPlanFitCreate(
        planning_date=data.planning_date,
        meal_type=data.meal_type,
        daily_nutrition_state_id=data.daily_nutrition_state_id,
        candidate=MealRecommendationCandidateInput(
            candidate_kind="recipe",
            composition_id=composition.id,
            quantity=data.quantity,
            quantity_unit=data.quantity_unit,
        ),
    )
    try:
        baseline_fit = evaluate_meal_plan_fit(db, person_id=person.id, data=baseline_input)
    except MealPlanFitError as exc:
        raise MealTransformationError(str(exc)) from exc

    daily_state = _load_daily_state(
        db,
        person_id=person.id,
        planning_date=data.planning_date,
        state_id=data.daily_nutrition_state_id,
    )
    baseline_candidate = build_recipe_candidate(
        composition,
        quantity=data.quantity,
        quantity_unit=data.quantity_unit,
    )
    try:
        candidate_factor = _candidate_portion_factor(
            composition,
            quantity=data.quantity,
            quantity_unit=data.quantity_unit,
        )
    except UnsupportedUnitConversionError as exc:
        raise MealTransformationError(
            "Recipe quantity cannot be converted safely to its nutrition reference unit."
        ) from exc

    ingredient_ids = [ingredient.food_item_id for ingredient in recipe.ingredients]
    source_profiles = list(
        db.scalars(
            select(FoodTransformationProfile)
            .options(*_profile_options())
            .where(
                FoodTransformationProfile.family_id == person.family_id,
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
                    FoodTransformationProfile.family_id == person.family_id,
                    FoodTransformationProfile.substitution_group.in_(groups),
                    FoodTransformationProfile.auto_transform_enabled.is_(True),
                    FoodItem.food_kind == "ingredient",
                    FoodItem.is_active.is_(True),
                    or_(FoodItem.family_id == person.family_id, FoodItem.family_id.is_(None)),
                )
            ).all()
        )

    alternatives_by_group: dict[str, list[FoodTransformationProfile]] = {}
    for profile in alternatives:
        alternatives_by_group.setdefault(profile.substitution_group, []).append(profile)

    proposals: list[MealTransformationProposalRead] = []
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
            original_snapshot = scale_composition_nutrition(
                original_composition,
                quantity=ingredient.quantity,
                quantity_unit=ingredient.unit,
            )
        except UnsupportedUnitConversionError:
            limitations.append(
                f"unsupported_source_unit:{ingredient.food_item.catalog_key}:{ingredient.unit}"
            )
            continue

        for target_profile in alternatives_by_group.get(source_profile.substitution_group, []):
            replacement = target_profile.food_item
            if replacement.id == ingredient.food_item_id:
                continue
            replacement_composition = _latest_food_composition(replacement)
            if replacement_composition is None:
                limitations.append(f"missing_replacement_composition:{replacement.catalog_key}")
                continue
            try:
                replacement_quantity, replacement_unit = _replacement_quantity(
                    ingredient,
                    source_profile,
                    target_profile,
                )
                replacement_snapshot = scale_composition_nutrition(
                    replacement_composition,
                    quantity=replacement_quantity,
                    quantity_unit=replacement_unit,
                )
                nutrition = _transformed_nutrition(
                    baseline_candidate.nutrition,
                    original=original_snapshot,
                    replacement=replacement_snapshot,
                    candidate_factor=candidate_factor,
                )
            except (UnsupportedUnitConversionError, MealTransformationError):
                limitations.append(
                    f"insufficient_replacement_evidence:{replacement.catalog_key}"
                )
                continue

            transformed = MealCandidate(
                key=recipe.recipe_key,
                name=recipe.name,
                kind="recipe",
                quantity=data.quantity,
                quantity_unit=data.quantity_unit,
                nutrition=nutrition,
                subjects=_transformed_subjects(
                    recipe,
                    source_ingredient_id=ingredient.id,
                    replacement=replacement,
                ),
                recipe=recipe,
                recipe_composition=composition,
                portion_factor=candidate_factor,
            )
            after_fit = _evaluate_loaded_candidate(
                db,
                person=person,
                candidate=transformed,
                planning_date=data.planning_date,
                meal_type=data.meal_type,
                daily_state=daily_state,
            )
            if not _is_improvement(baseline_fit, after_fit):
                continue

            proposals.append(
                MealTransformationProposalRead(
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
                    before_fit=baseline_fit,
                    after_fit=after_fit,
                    fit_score_delta=_fit_delta(baseline_fit, after_fit),
                    resolves_mandatory_block=(after_fit.eligible and not baseline_fit.eligible),
                    changed_rule_ids=_changed_rule_ids(baseline_fit, after_fit),
                    explanation=_proposal_explanation(baseline_fit, after_fit),
                )
            )

    proposals.sort(
        key=lambda item: (
            item.resolves_mandatory_block,
            item.after_fit.eligible,
            item.after_fit.fit_score if item.after_fit.fit_score is not None else Decimal("-1"),
            item.fit_score_delta if item.fit_score_delta is not None else Decimal("-1"),
        ),
        reverse=True,
    )

    return MealTransformationRead(
        person_id=person.id,
        recipe_id=recipe.id,
        recipe_name=recipe.name,
        planning_date=data.planning_date,
        meal_type=data.meal_type,
        baseline_fit=baseline_fit,
        proposals=proposals[: data.max_proposals],
        limitations=sorted(set(limitations)),
    )
