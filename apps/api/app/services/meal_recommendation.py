from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from app.models.daily_nutrition_state import DailyNutritionState
from app.models.food_adverse_reaction import FoodAdverseReaction
from app.models.food_catalog import (
    FoodCompositionSnapshot,
    FoodItem,
    Recipe,
    RecipeCompositionSnapshot,
)
from app.models.food_preference import FoodPreference
from app.models.nutrition_constraint import NutritionConstraint
from app.services.serving_nutrition import (
    NutritionSnapshot,
    UnsupportedUnitConversionError,
    convert_quantity,
    scale_composition_nutrition,
)

SCORE_QUANTUM = Decimal("0.0001")
ZERO = Decimal(0)
ONE = Decimal(1)


class MealRecommendationError(ValueError):
    pass


class UnsupportedMandatoryConstraintError(MealRecommendationError):
    pass


@dataclass(frozen=True)
class MealCandidate:
    key: str
    name: str
    kind: str
    quantity: Decimal
    quantity_unit: str
    nutrition: NutritionSnapshot
    subjects: frozenset[tuple[str, str]]
    food_item: FoodItem | None = None
    recipe: Recipe | None = None
    food_composition: FoodCompositionSnapshot | None = None
    recipe_composition: RecipeCompositionSnapshot | None = None


@dataclass(frozen=True)
class CandidateEvaluation:
    candidate: MealCandidate
    eligible: bool
    rank: int | None
    score: Decimal | None
    score_breakdown: dict[str, Decimal]
    exclusion_reasons: tuple[str, ...]
    explanation: tuple[str, ...]


@dataclass(frozen=True)
class RecommendationResult:
    engine_version: str
    evaluations: tuple[CandidateEvaluation, ...]

    @property
    def eligible(self) -> tuple[CandidateEvaluation, ...]:
        return tuple(evaluation for evaluation in self.evaluations if evaluation.eligible)


def _active_on(start_date: date | None, end_date: date | None, on_date: date) -> bool:
    if start_date is not None and on_date < start_date:
        return False
    return end_date is None or on_date <= end_date


def _food_subjects(food_item: FoodItem) -> set[tuple[str, str]]:
    return {
        ("food", food_item.catalog_key),
        ("food_item", food_item.catalog_key),
        (food_item.food_kind, food_item.catalog_key),
    }


def build_food_candidate(
    composition: FoodCompositionSnapshot,
    *,
    quantity: Decimal,
    quantity_unit: str,
) -> MealCandidate:
    food_item = composition.food_item
    return MealCandidate(
        key=food_item.catalog_key,
        name=food_item.name,
        kind="food_item",
        quantity=quantity,
        quantity_unit=quantity_unit,
        nutrition=scale_composition_nutrition(
            composition,
            quantity=quantity,
            quantity_unit=quantity_unit,
        ),
        subjects=frozenset(_food_subjects(food_item)),
        food_item=food_item,
        food_composition=composition,
    )


def build_recipe_candidate(
    composition: RecipeCompositionSnapshot,
    *,
    quantity: Decimal,
    quantity_unit: str,
) -> MealCandidate:
    recipe = composition.recipe
    subjects: set[tuple[str, str]] = {
        ("recipe", recipe.recipe_key),
    }
    for ingredient in recipe.ingredients:
        subjects.update(_food_subjects(ingredient.food_item))

    return MealCandidate(
        key=recipe.recipe_key,
        name=recipe.name,
        kind="recipe",
        quantity=quantity,
        quantity_unit=quantity_unit,
        nutrition=scale_composition_nutrition(
            composition,
            quantity=quantity,
            quantity_unit=quantity_unit,
        ),
        subjects=frozenset(subjects),
        recipe=recipe,
        recipe_composition=composition,
    )


def _subject_matches(subject_type: str, subject_key: str, candidate: MealCandidate) -> bool:
    return (subject_type, subject_key) in candidate.subjects


def _convert_or_raise(value: Decimal, from_unit: str, to_unit: str, *, context: str) -> Decimal:
    try:
        return convert_quantity(value, from_unit, to_unit)
    except UnsupportedUnitConversionError as exc:
        raise UnsupportedMandatoryConstraintError(
            f"Cannot evaluate mandatory constraint {context}: {from_unit!r} and {to_unit!r} "
            "are not safely convertible."
        ) from exc


def _current_nutrient_total(
    daily_state: DailyNutritionState,
    nutrient_key: str,
    target_unit: str,
) -> Decimal:
    for component in daily_state.components:
        if component.target_type != "nutrient" or component.target_key != nutrient_key:
            continue
        consumed = component.consumed_value or ZERO
        planned = component.planned_value or ZERO
        total = consumed + planned
        return _convert_or_raise(
            total,
            component.unit,
            target_unit,
            context=f"for nutrient {nutrient_key!r}",
        )
    return ZERO


def _mandatory_constraint_exclusion(
    constraint: NutritionConstraint,
    candidate: MealCandidate,
    daily_state: DailyNutritionState,
) -> str | None:
    if constraint.operator == "exclude" and constraint.target_type in {
        "food",
        "food_item",
        "ingredient",
        "product",
        "dish",
        "beverage",
        "supplement",
        "generic",
        "recipe",
    }:
        if _subject_matches(constraint.target_type, constraint.target_key, candidate):
            return f"mandatory_exclusion:{constraint.target_type}:{constraint.target_key}"
        return None

    if constraint.target_type == "nutrient" and constraint.operator in {"max", "lte", "<="}:
        if constraint.unit is None or constraint.value_max is None:
            raise UnsupportedMandatoryConstraintError(
                f"Mandatory nutrient maximum {constraint.target_key!r} requires value_max and unit."
            )
        nutrient = candidate.nutrition.nutrients.get(constraint.target_key)
        if nutrient is None:
            return f"mandatory_nutrient_data_missing:{constraint.target_key}"
        candidate_value = _convert_or_raise(
            nutrient.value,
            nutrient.unit,
            constraint.unit,
            context=f"for nutrient {constraint.target_key!r}",
        )
        current_value = _current_nutrient_total(
            daily_state,
            constraint.target_key,
            constraint.unit,
        )
        if current_value + candidate_value > constraint.value_max:
            return f"mandatory_nutrient_max:{constraint.target_key}"
        return None

    raise UnsupportedMandatoryConstraintError(
        "The recommendation engine does not yet support mandatory constraint "
        f"{constraint.target_type!r}/{constraint.operator!r}/{constraint.target_key!r}."
    )


def _preference_score(
    candidate: MealCandidate,
    preferences: list[FoodPreference],
    planning_date: date,
) -> tuple[Decimal, list[str]]:
    score = ZERO
    reasons: list[str] = []
    for preference in preferences:
        if not _active_on(preference.start_date, preference.end_date, planning_date):
            continue
        if not _subject_matches(preference.subject_type, preference.subject_key, candidate):
            continue

        weight = Decimal(preference.intensity) / Decimal(5)
        if preference.preference_type == "like":
            score += weight
            reasons.append(f"preferred:{preference.subject_type}:{preference.subject_key}")
        elif preference.preference_type == "dislike":
            score -= weight
            reasons.append(f"disliked:{preference.subject_type}:{preference.subject_key}")

    return score, reasons


def _advisory_reaction_score(
    candidate: MealCandidate,
    reactions: list[FoodAdverseReaction],
    planning_date: date,
) -> tuple[Decimal, list[str]]:
    penalty = ZERO
    reasons: list[str] = []
    for reaction in reactions:
        if reaction.is_mandatory:
            continue
        if not _active_on(reaction.start_date, reaction.end_date, planning_date):
            continue
        if not _subject_matches(reaction.subject_type, reaction.subject_key, candidate):
            continue
        penalty -= ONE
        reasons.append(f"advisory_reaction:{reaction.subject_type}:{reaction.subject_key}")
    return penalty, reasons


def _energy_score(candidate: MealCandidate, daily_state: DailyNutritionState) -> tuple[Decimal, str | None]:
    energy = candidate.nutrition.energy_kcal
    if energy is None:
        return ZERO, None

    remaining_min = daily_state.energy_remaining_min_kcal
    remaining_max = daily_state.energy_remaining_max_kcal
    if remaining_min is None and remaining_max is None:
        return ZERO, None

    if remaining_max is not None and remaining_max <= ZERO:
        return -ONE, "energy_target_already_exceeded"

    if remaining_min is not None and remaining_max is not None:
        target = max((remaining_min + remaining_max) / Decimal(2), ONE)
    elif remaining_min is not None:
        target = max(remaining_min, ONE)
    else:
        target = max(remaining_max or ONE, ONE)

    distance = abs(energy - target) / target
    score = max(-ONE, ONE - distance)
    if remaining_max is not None and energy > remaining_max:
        score -= ONE
        return score, "candidate_exceeds_remaining_energy_max"
    return score, "candidate_fits_remaining_energy"


def _nutrient_score(
    candidate: MealCandidate,
    daily_state: DailyNutritionState,
) -> tuple[Decimal, list[str]]:
    score = ZERO
    reasons: list[str] = []
    for component in daily_state.components:
        if component.target_type != "nutrient":
            continue
        nutrient = candidate.nutrition.nutrients.get(component.target_key)
        if nutrient is None:
            continue
        try:
            value = convert_quantity(nutrient.value, nutrient.unit, component.unit)
        except UnsupportedUnitConversionError:
            continue

        if component.remaining_min is not None and component.remaining_min > ZERO:
            contribution = min(value / component.remaining_min, ONE)
            score += contribution
            if contribution > ZERO:
                reasons.append(f"supports_deficit:{component.target_key}")

        if (
            component.remaining_max is not None
            and component.remaining_max >= ZERO
            and value > component.remaining_max
        ):
            score -= ONE
            reasons.append(f"exceeds_remaining_max:{component.target_key}")

    return score, reasons


def recommend_meals(
    *,
    daily_state: DailyNutritionState,
    candidates: list[MealCandidate],
    preferences: list[FoodPreference],
    adverse_reactions: list[FoodAdverseReaction],
    constraints: list[NutritionConstraint],
    planning_date: date,
    engine_version: str = "meal-recommendation-v1",
) -> RecommendationResult:
    active_mandatory_constraints = [
        constraint
        for constraint in constraints
        if constraint.is_mandatory
        and _active_on(constraint.start_date, constraint.end_date, planning_date)
    ]

    provisional: list[CandidateEvaluation] = []
    for candidate in candidates:
        exclusions: list[str] = []
        explanations: list[str] = []

        for reaction in adverse_reactions:
            if not reaction.is_mandatory:
                continue
            if not _active_on(reaction.start_date, reaction.end_date, planning_date):
                continue
            if _subject_matches(reaction.subject_type, reaction.subject_key, candidate):
                exclusions.append(
                    f"mandatory_reaction:{reaction.subject_type}:{reaction.subject_key}"
                )

        for constraint in active_mandatory_constraints:
            exclusion = _mandatory_constraint_exclusion(constraint, candidate, daily_state)
            if exclusion is not None:
                exclusions.append(exclusion)

        if exclusions:
            provisional.append(
                CandidateEvaluation(
                    candidate=candidate,
                    eligible=False,
                    rank=None,
                    score=None,
                    score_breakdown={},
                    exclusion_reasons=tuple(sorted(set(exclusions))),
                    explanation=("Excluded by a non-negotiable safety or nutrition rule.",),
                )
            )
            continue

        energy_score, energy_reason = _energy_score(candidate, daily_state)
        nutrient_score, nutrient_reasons = _nutrient_score(candidate, daily_state)
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
            "energy": energy_score,
            "nutrients": nutrient_score,
            "preferences": preference_score,
            "advisory_reactions": reaction_score,
        }
        total_score = sum(score_breakdown.values(), start=ZERO).quantize(
            SCORE_QUANTUM,
            rounding=ROUND_HALF_UP,
        )
        if energy_reason is not None:
            explanations.append(energy_reason)
        explanations.extend(nutrient_reasons)
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
