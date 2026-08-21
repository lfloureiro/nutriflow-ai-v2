import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.food_catalog import FoodCompositionSnapshot, RecipeCompositionSnapshot
from app.models.meal import MealEvent, MealParticipant, Serving
from app.models.person import Person
from app.services.serving_nutrition import calculate_serving_nutrition
from app.services.shared_family_meal import (
    SharedFamilyMealRecommendationResult,
    SharedMealCandidateEvaluation,
    SharedMealParticipantEvaluation,
)


class SharedFamilyMealPlanningError(ValueError):
    pass


@dataclass(frozen=True)
class PlannedSharedFamilyParticipant:
    person: Person
    meal_participant: MealParticipant
    serving: Serving


@dataclass(frozen=True)
class PlannedSharedFamilyMealResult:
    meal_event: MealEvent
    selected_evaluation: SharedMealCandidateEvaluation
    participants: tuple[PlannedSharedFamilyParticipant, ...]

    @property
    def servings(self) -> tuple[Serving, ...]:
        return tuple(participant.serving for participant in self.participants)


def _is_timezone_aware(value: datetime) -> bool:
    return value.tzinfo is not None and value.utcoffset() is not None


def _select_candidate(
    recommendation: SharedFamilyMealRecommendationResult,
    candidate_key: str,
) -> SharedMealCandidateEvaluation:
    matches = [
        evaluation
        for evaluation in recommendation.evaluations
        if evaluation.candidate_key == candidate_key
    ]
    if len(matches) != 1:
        raise SharedFamilyMealPlanningError(
            "candidate_key must identify exactly one shared-family recommendation option."
        )

    selected = matches[0]
    if not selected.eligible or selected.rank is None:
        raise SharedFamilyMealPlanningError(
            "An ineligible shared-family recommendation cannot create a planned meal."
        )
    if len(selected.participant_evaluations) < 2:
        raise SharedFamilyMealPlanningError(
            "A shared-family planned meal requires at least two participant evaluations."
        )
    return selected


def _load_person(
    session: Session,
    participant: SharedMealParticipantEvaluation,
) -> Person:
    person_id = participant.person.id
    if person_id is None:
        raise SharedFamilyMealPlanningError(
            "Shared-family recommendation Persons must be persisted before materialization."
        )

    person = session.get(Person, person_id)
    if person is None:
        raise SharedFamilyMealPlanningError(
            "A shared-family recommendation Person no longer exists."
        )
    if participant.portion.person_id != person.id:
        raise SharedFamilyMealPlanningError(
            "Shared-family recommendation portion does not belong to its Person."
        )
    return person


def _load_composition(
    session: Session,
    participant: SharedMealParticipantEvaluation,
) -> FoodCompositionSnapshot | RecipeCompositionSnapshot:
    candidate = participant.evaluation.candidate
    food_composition = candidate.food_composition
    recipe_composition = candidate.recipe_composition
    if (food_composition is None) == (recipe_composition is None):
        raise SharedFamilyMealPlanningError(
            "Each shared-family participant candidate must reference exactly one composition."
        )

    if food_composition is not None and food_composition.id is None:
        raise SharedFamilyMealPlanningError(
            "Shared-family Food composition must be persisted before materialization."
        )
    if food_composition is not None:
        persisted_food = session.get(FoodCompositionSnapshot, food_composition.id)
        if persisted_food is None:
            raise SharedFamilyMealPlanningError(
                "The Food composition used by the shared recommendation no longer exists."
            )
        return persisted_food

    if recipe_composition is None or recipe_composition.id is None:
        raise SharedFamilyMealPlanningError(
            "Shared-family Recipe composition must be persisted before materialization."
        )
    persisted_recipe = session.get(RecipeCompositionSnapshot, recipe_composition.id)
    if persisted_recipe is None:
        raise SharedFamilyMealPlanningError(
            "The Recipe composition used by the shared recommendation no longer exists."
        )
    return persisted_recipe


def _validate_participant_candidate(
    selected: SharedMealCandidateEvaluation,
    participant: SharedMealParticipantEvaluation,
) -> None:
    evaluation = participant.evaluation
    candidate = evaluation.candidate
    portion = participant.portion

    if not evaluation.eligible:
        raise SharedFamilyMealPlanningError(
            "Every participant must remain eligible for the selected shared-family meal."
        )
    if candidate.key != selected.candidate_key:
        raise SharedFamilyMealPlanningError(
            "Participant candidate key does not match the selected shared-family option."
        )
    if candidate.name != selected.candidate_name or candidate.kind != selected.candidate_kind:
        raise SharedFamilyMealPlanningError(
            "Participant candidate identity does not match the selected shared-family option."
        )
    if candidate.quantity != portion.quantity or candidate.quantity_unit != portion.quantity_unit:
        raise SharedFamilyMealPlanningError(
            "Participant candidate quantity does not match the recommended shared portion."
        )


def _validate_composition_identity(
    selected: SharedMealCandidateEvaluation,
    composition: FoodCompositionSnapshot | RecipeCompositionSnapshot,
    family_id: uuid.UUID,
) -> None:
    if isinstance(composition, FoodCompositionSnapshot):
        food_item = composition.food_item
        if selected.candidate_kind != "food_item" or food_item.catalog_key != selected.candidate_key:
            raise SharedFamilyMealPlanningError(
                "Persisted Food composition does not match the selected shared-family option."
            )
        if food_item.family_id is not None and food_item.family_id != family_id:
            raise SharedFamilyMealPlanningError(
                "The selected Family-specific Food belongs to a different Family."
            )
        return

    recipe = composition.recipe
    if selected.candidate_kind != "recipe" or recipe.recipe_key != selected.candidate_key:
        raise SharedFamilyMealPlanningError(
            "Persisted Recipe composition does not match the selected shared-family option."
        )
    if recipe.family_id is not None and recipe.family_id != family_id:
        raise SharedFamilyMealPlanningError(
            "The selected Family-specific Recipe belongs to a different Family."
        )


def materialize_shared_family_recommendation(
    session: Session,
    *,
    recommendation: SharedFamilyMealRecommendationResult,
    candidate_key: str,
    scheduled_at: datetime,
    timezone: str,
    meal_type: str,
    title: str | None = None,
    location: str | None = None,
    notes: str | None = None,
    calculation_version: str = "serving-nutrition-v1",
) -> PlannedSharedFamilyMealResult:
    if not recommendation.engine_version:
        raise SharedFamilyMealPlanningError("recommendation engine_version must not be empty.")
    if not candidate_key:
        raise SharedFamilyMealPlanningError("candidate_key must not be empty.")
    if not _is_timezone_aware(scheduled_at):
        raise SharedFamilyMealPlanningError("scheduled_at must be timezone-aware.")
    if not timezone:
        raise SharedFamilyMealPlanningError("timezone must not be empty.")
    if not meal_type:
        raise SharedFamilyMealPlanningError("meal_type must not be empty.")

    selected = _select_candidate(recommendation, candidate_key)
    source_reference = f"shared-family-recommendation:{recommendation.engine_version}"
    if len(source_reference) > 255:
        raise SharedFamilyMealPlanningError("recommendation engine_version is too long to persist.")

    loaded: list[
        tuple[
            SharedMealParticipantEvaluation,
            Person,
            FoodCompositionSnapshot | RecipeCompositionSnapshot,
        ]
    ] = []
    family_id: uuid.UUID | None = None
    seen_person_ids: set[uuid.UUID] = set()
    for participant in selected.participant_evaluations:
        _validate_participant_candidate(selected, participant)
        person = _load_person(session, participant)
        if person.id in seen_person_ids:
            raise SharedFamilyMealPlanningError(
                "Each Person may appear only once in a shared-family planned meal."
            )
        seen_person_ids.add(person.id)

        if family_id is None:
            family_id = person.family_id
        elif person.family_id != family_id:
            raise SharedFamilyMealPlanningError(
                "All shared-family planned-meal participants must belong to the same Family."
            )

        composition = _load_composition(session, participant)
        _validate_composition_identity(selected, composition, person.family_id)
        loaded.append((participant, person, composition))

    if family_id is None:
        raise SharedFamilyMealPlanningError("Shared-family recommendation has no participants.")

    event = MealEvent(
        family_id=family_id,
        meal_type=meal_type,
        title=title or selected.candidate_name,
        scheduled_at=scheduled_at,
        timezone=timezone,
        status="planned",
        location=location,
        source="recommendation",
        source_reference=source_reference,
        notes=notes,
    )

    planned_participants: list[PlannedSharedFamilyParticipant] = []
    for participant_evaluation, person, composition in loaded:
        portion = participant_evaluation.portion
        meal_participant = MealParticipant(
            meal_event=event,
            person=person,
            status="planned",
        )
        serving = Serving(
            meal_participant=meal_participant,
            item_type=selected.candidate_kind,
            item_key=selected.candidate_key,
            item_name=selected.candidate_name,
            status="planned",
            quantity_planned=portion.quantity,
            quantity_unit=portion.quantity_unit,
            nutrition_source="catalog",
            source_reference=source_reference,
        )
        calculate_serving_nutrition(
            serving,
            composition,
            calculation_version=calculation_version,
        )
        planned_participants.append(
            PlannedSharedFamilyParticipant(
                person=person,
                meal_participant=meal_participant,
                serving=serving,
            )
        )

    session.add(event)
    return PlannedSharedFamilyMealResult(
        meal_event=event,
        selected_evaluation=selected,
        participants=tuple(planned_participants),
    )
