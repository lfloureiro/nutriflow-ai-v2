import uuid
from dataclasses import dataclass, replace
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from app.models.daily_nutrition_state import DailyNutritionState
from app.models.food_adverse_reaction import FoodAdverseReaction
from app.models.food_catalog import FoodCompositionSnapshot, RecipeCompositionSnapshot
from app.models.food_preference import FoodPreference
from app.models.nutrition_constraint import NutritionConstraint
from app.models.person import Person
from app.services.meal_recommendation import (
    CandidateEvaluation,
    MealCandidate,
    build_food_candidate,
    build_recipe_candidate,
    recommend_meals,
)
from app.services.recommendation_practical_context import (
    CandidatePracticalProfile,
    PracticalMealContext,
    recommend_meals_with_practical_context,
)

ZERO = Decimal(0)
SCORE_QUANTUM = Decimal("0.0001")


class SharedFamilyMealError(ValueError):
    pass


@dataclass(frozen=True)
class SharedMealPortion:
    person_id: uuid.UUID
    quantity: Decimal
    quantity_unit: str
    portion_factor: Decimal | None = None
    meal_energy_target_min_kcal: Decimal | None = None
    meal_energy_target_max_kcal: Decimal | None = None
    energy_allocation_policy: str | None = None


@dataclass(frozen=True)
class SharedMealCandidateProposal:
    portions: tuple[SharedMealPortion, ...]
    food_composition: FoodCompositionSnapshot | None = None
    recipe_composition: RecipeCompositionSnapshot | None = None


@dataclass(frozen=True)
class SharedMealParticipantContext:
    person: Person
    daily_state: DailyNutritionState
    preferences: tuple[FoodPreference, ...] = ()
    adverse_reactions: tuple[FoodAdverseReaction, ...] = ()
    constraints: tuple[NutritionConstraint, ...] = ()
    practical_context: PracticalMealContext | None = None
    practical_profiles: tuple[CandidatePracticalProfile, ...] = ()


@dataclass(frozen=True)
class SharedMealParticipantEvaluation:
    person: Person
    portion: SharedMealPortion
    evaluation: CandidateEvaluation


@dataclass(frozen=True)
class SharedMealCandidateEvaluation:
    candidate_key: str
    candidate_name: str
    candidate_kind: str
    eligible: bool
    rank: int | None
    minimum_score: Decimal | None
    average_score: Decimal | None
    participant_evaluations: tuple[SharedMealParticipantEvaluation, ...]
    exclusion_reasons: tuple[str, ...]


@dataclass(frozen=True)
class SharedFamilyMealRecommendationResult:
    engine_version: str
    evaluations: tuple[SharedMealCandidateEvaluation, ...]

    @property
    def eligible(self) -> tuple[SharedMealCandidateEvaluation, ...]:
        return tuple(evaluation for evaluation in self.evaluations if evaluation.eligible)


def _validate_participants(
    participants: tuple[SharedMealParticipantContext, ...],
) -> uuid.UUID:
    if len(participants) < 2:
        raise SharedFamilyMealError("A shared-family recommendation requires at least two Persons.")

    person_ids: set[uuid.UUID] = set()
    family_ids: set[uuid.UUID] = set()
    for participant in participants:
        person = participant.person
        if person.id is None or person.family_id is None:
            raise SharedFamilyMealError(
                "Persons must be persisted before shared-family recommendation."
            )
        if person.id in person_ids:
            raise SharedFamilyMealError("Each Person may appear only once in shared-family context.")
        if participant.daily_state.person_id != person.id:
            raise SharedFamilyMealError(
                "Each DailyNutritionState must belong to its shared-family Person."
            )
        person_ids.add(person.id)
        family_ids.add(person.family_id)

    if len(family_ids) != 1:
        raise SharedFamilyMealError("All shared-meal participants must belong to the same Family.")
    return next(iter(family_ids))


def _proposal_identity(
    proposal: SharedMealCandidateProposal,
) -> tuple[str, str, str, uuid.UUID | None]:
    if (proposal.food_composition is None) == (proposal.recipe_composition is None):
        raise SharedFamilyMealError(
            "A shared-meal proposal must reference exactly one Food or Recipe composition."
        )

    if proposal.food_composition is not None:
        food_item = proposal.food_composition.food_item
        return food_item.catalog_key, food_item.name, "food_item", food_item.family_id

    recipe_composition = proposal.recipe_composition
    if recipe_composition is None:
        raise SharedFamilyMealError("Shared-meal Recipe composition is unavailable.")
    recipe = recipe_composition.recipe
    return recipe.recipe_key, recipe.name, "recipe", recipe.family_id


def _portion_map(
    proposal: SharedMealCandidateProposal,
    participant_ids: set[uuid.UUID],
) -> dict[uuid.UUID, SharedMealPortion]:
    portions: dict[uuid.UUID, SharedMealPortion] = {}
    for portion in proposal.portions:
        if portion.person_id in portions:
            raise SharedFamilyMealError(
                "A shared-meal proposal cannot define two portions for the same Person."
            )
        if portion.quantity <= ZERO:
            raise SharedFamilyMealError("Shared-meal portions must be positive.")
        if not portion.quantity_unit:
            raise SharedFamilyMealError("Shared-meal portion units must not be empty.")
        portions[portion.person_id] = portion

    if set(portions) != participant_ids:
        raise SharedFamilyMealError(
            "Every shared-meal proposal must define exactly one portion for every participant."
        )
    return portions


def _build_candidate(
    proposal: SharedMealCandidateProposal,
    portion: SharedMealPortion,
) -> MealCandidate:
    if proposal.food_composition is not None:
        candidate = build_food_candidate(
            proposal.food_composition,
            quantity=portion.quantity,
            quantity_unit=portion.quantity_unit,
        )
    elif proposal.recipe_composition is not None:
        candidate = build_recipe_candidate(
            proposal.recipe_composition,
            quantity=portion.quantity,
            quantity_unit=portion.quantity_unit,
        )
    else:
        raise SharedFamilyMealError("Shared-meal proposal composition is unavailable.")

    return replace(
        candidate,
        portion_factor=portion.portion_factor,
        meal_energy_target_min_kcal=portion.meal_energy_target_min_kcal,
        meal_energy_target_max_kcal=portion.meal_energy_target_max_kcal,
        energy_allocation_policy=portion.energy_allocation_policy,
    )


def _evaluate_participant(
    participant: SharedMealParticipantContext,
    candidate: MealCandidate,
    *,
    planning_date: date,
    engine_version: str,
) -> CandidateEvaluation:
    if participant.practical_context is not None:
        result = recommend_meals_with_practical_context(
            daily_state=participant.daily_state,
            candidates=[candidate],
            preferences=list(participant.preferences),
            adverse_reactions=list(participant.adverse_reactions),
            constraints=list(participant.constraints),
            planning_date=planning_date,
            practical_context=participant.practical_context,
            practical_profiles=participant.practical_profiles,
            engine_version=engine_version,
        )
    else:
        result = recommend_meals(
            daily_state=participant.daily_state,
            candidates=[candidate],
            preferences=list(participant.preferences),
            adverse_reactions=list(participant.adverse_reactions),
            constraints=list(participant.constraints),
            planning_date=planning_date,
            engine_version=engine_version,
        )

    if len(result.evaluations) != 1:
        raise SharedFamilyMealError(
            "Participant recommendation must return exactly one candidate evaluation."
        )
    return result.evaluations[0]


def _score_summary(
    evaluations: tuple[SharedMealParticipantEvaluation, ...],
) -> tuple[Decimal | None, Decimal | None]:
    if any(not evaluation.evaluation.eligible for evaluation in evaluations):
        return None, None

    scores: list[Decimal] = []
    for participant_evaluation in evaluations:
        score = participant_evaluation.evaluation.score
        if score is None:
            raise SharedFamilyMealError("Eligible participant evaluation is missing its score.")
        scores.append(score)

    minimum = min(scores).quantize(SCORE_QUANTUM, rounding=ROUND_HALF_UP)
    average = (sum(scores, start=ZERO) / Decimal(len(scores))).quantize(
        SCORE_QUANTUM,
        rounding=ROUND_HALF_UP,
    )
    return minimum, average


def _participant_exclusions(
    evaluations: tuple[SharedMealParticipantEvaluation, ...],
) -> tuple[str, ...]:
    reasons = {
        f"person:{participant.person.id}:{reason}"
        for participant in evaluations
        for reason in participant.evaluation.exclusion_reasons
    }
    return tuple(sorted(reasons))


def recommend_shared_family_meals(
    *,
    participants: tuple[SharedMealParticipantContext, ...],
    proposals: tuple[SharedMealCandidateProposal, ...],
    planning_date: date,
    engine_version: str = "shared-family-meal-v1",
) -> SharedFamilyMealRecommendationResult:
    if not engine_version:
        raise SharedFamilyMealError("engine_version must not be empty.")

    family_id = _validate_participants(participants)
    participant_ids = {participant.person.id for participant in participants}
    if None in participant_ids:
        raise SharedFamilyMealError("Shared-family participants must be persisted.")
    typed_participant_ids = {person_id for person_id in participant_ids if person_id is not None}

    provisional: list[SharedMealCandidateEvaluation] = []
    candidate_keys: set[str] = set()
    for proposal in proposals:
        candidate_key, candidate_name, candidate_kind, catalog_family_id = _proposal_identity(proposal)
        if candidate_key in candidate_keys:
            raise SharedFamilyMealError(
                f"Duplicate shared-meal candidate key: {candidate_key!r}."
            )
        candidate_keys.add(candidate_key)
        if catalog_family_id is not None and catalog_family_id != family_id:
            raise SharedFamilyMealError(
                "A Family-specific shared-meal candidate belongs to a different Family."
            )

        portions = _portion_map(proposal, typed_participant_ids)
        participant_evaluations: list[SharedMealParticipantEvaluation] = []
        for participant in participants:
            person_id = participant.person.id
            if person_id is None:
                raise SharedFamilyMealError("Shared-family participant is not persisted.")
            portion = portions[person_id]
            candidate = _build_candidate(proposal, portion)
            evaluation = _evaluate_participant(
                participant,
                candidate,
                planning_date=planning_date,
                engine_version=engine_version,
            )
            participant_evaluations.append(
                SharedMealParticipantEvaluation(
                    person=participant.person,
                    portion=portion,
                    evaluation=evaluation,
                )
            )

        participant_tuple = tuple(participant_evaluations)
        minimum_score, average_score = _score_summary(participant_tuple)
        eligible = all(item.evaluation.eligible for item in participant_tuple)
        provisional.append(
            SharedMealCandidateEvaluation(
                candidate_key=candidate_key,
                candidate_name=candidate_name,
                candidate_kind=candidate_kind,
                eligible=eligible,
                rank=None,
                minimum_score=minimum_score,
                average_score=average_score,
                participant_evaluations=participant_tuple,
                exclusion_reasons=_participant_exclusions(participant_tuple),
            )
        )

    eligible_sorted = sorted(
        (evaluation for evaluation in provisional if evaluation.eligible),
        key=lambda evaluation: (
            -(evaluation.minimum_score or ZERO),
            -(evaluation.average_score or ZERO),
            evaluation.candidate_key,
        ),
    )
    rank_by_key = {
        evaluation.candidate_key: rank
        for rank, evaluation in enumerate(eligible_sorted, start=1)
    }

    ranked = [
        replace(evaluation, rank=rank_by_key.get(evaluation.candidate_key))
        for evaluation in provisional
    ]
    ranked.sort(
        key=lambda evaluation: (
            0 if evaluation.eligible else 1,
            evaluation.rank if evaluation.rank is not None else 10**9,
            evaluation.candidate_key,
        )
    )
    return SharedFamilyMealRecommendationResult(
        engine_version=engine_version,
        evaluations=tuple(ranked),
    )
