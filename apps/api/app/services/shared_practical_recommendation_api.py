import uuid

from sqlalchemy.orm import Session

from app.models.daily_nutrition_state import DailyNutritionState
from app.models.family import Family
from app.models.person import Person
from app.schemas.practical_recommendation import (
    CommercialOfferRead,
    PracticalMealRecommendationCreate,
)
from app.schemas.shared_practical_recommendation import (
    SharedParticipantEvaluationRead,
    SharedPracticalPlanCreate,
    SharedPracticalPlanRead,
    SharedPracticalRecommendationCreate,
    SharedPracticalRecommendationRead,
    SharedRecommendationOptionRead,
)
from app.services.commercial_availability import CommercialOfferSnapshot
from app.services.meal_recommendation import MealCandidate
from app.services.meal_recommendation_api import load_recommendation_inputs
from app.services.planning_bootstrap_api import get_planning_bootstrap
from app.services.practical_recommendation_api import (
    _build_practical_channels,
    _merge_source_channels,
)
from app.services.recommendation_practical_context import (
    CandidatePracticalProfile,
    PracticalMealContext,
)
from app.services.shared_family_meal import (
    SharedFamilyMealRecommendationResult,
    SharedMealCandidateProposal,
    SharedMealParticipantContext,
    SharedMealPortion,
    recommend_shared_family_meals,
)
from app.services.shared_family_meal_planning import materialize_shared_family_recommendation


class SharedPracticalRecommendationApiError(ValueError):
    pass


def _candidate_proposals(
    candidates: list[MealCandidate],
    person_ids: list[uuid.UUID],
) -> tuple[SharedMealCandidateProposal, ...]:
    proposals: list[SharedMealCandidateProposal] = []
    for candidate in candidates:
        proposals.append(
            SharedMealCandidateProposal(
                portions=tuple(
                    SharedMealPortion(
                        person_id=person_id,
                        quantity=candidate.quantity,
                        quantity_unit=candidate.quantity_unit,
                    )
                    for person_id in person_ids
                ),
                food_composition=candidate.food_composition,
                recipe_composition=candidate.recipe_composition,
            )
        )
    return tuple(proposals)


def _commercial_offer_read(offer: CommercialOfferSnapshot) -> CommercialOfferRead:
    return CommercialOfferRead(
        candidate_key=offer.candidate_key,
        source_kind=offer.source_kind,
        source_key=offer.source_key,
        location=offer.location,
        offer_key=offer.offer_key,
        provider_key=offer.provider_key,
        provider_name=offer.provider_name,
        item_price=offer.item_price,
        currency=offer.currency,
        delivery_fee=offer.delivery_fee,
        minimum_order=offer.minimum_order,
        total_known_price=offer.total_known_price,
        observed_at=offer.observed_at,
        source_reference=offer.source_reference,
    )


def _result_read(
    family: Family,
    data: SharedPracticalRecommendationCreate,
    result: SharedFamilyMealRecommendationResult,
    offers: list[CommercialOfferSnapshot],
) -> SharedPracticalRecommendationRead:
    options: list[SharedRecommendationOptionRead] = []
    for evaluation in result.evaluations:
        options.append(
            SharedRecommendationOptionRead(
                candidate_key=evaluation.candidate_key,
                candidate_name=evaluation.candidate_name,
                candidate_kind=evaluation.candidate_kind,
                eligible=evaluation.eligible,
                rank=evaluation.rank,
                minimum_score=evaluation.minimum_score,
                average_score=evaluation.average_score,
                exclusion_reasons=list(evaluation.exclusion_reasons),
                participants=[
                    SharedParticipantEvaluationRead(
                        person_id=participant.person.id,
                        score=participant.evaluation.score,
                        quantity=participant.portion.quantity,
                        quantity_unit=participant.portion.quantity_unit,
                        energy_kcal=participant.evaluation.candidate.nutrition.energy_kcal,
                        explanation=list(participant.evaluation.explanation),
                    )
                    for participant in evaluation.participant_evaluations
                ],
            )
        )

    return SharedPracticalRecommendationRead(
        family_id=family.id,
        person_ids=data.person_ids,
        planning_date=data.planning_date,
        scheduled_at=data.scheduled_at,
        meal_type=data.meal_type,
        engine_version=result.engine_version,
        source_kinds=sorted(set(data.source_kinds)),
        options=options,
        commercial_offers=[_commercial_offer_read(offer) for offer in offers],
    )


def _compute_shared_recommendation(
    session: Session,
    *,
    family: Family,
    data: SharedPracticalRecommendationCreate,
) -> tuple[SharedFamilyMealRecommendationResult, list[CommercialOfferSnapshot]]:
    if len(data.person_ids) != len(set(data.person_ids)):
        raise SharedPracticalRecommendationApiError(
            "Each Person can appear only once in a shared recommendation."
        )

    loaded: list[tuple[Person, DailyNutritionState]] = []
    first_candidates: list[MealCandidate] | None = None
    practical_profiles: tuple[CandidatePracticalProfile, ...] | None = None
    offers: list[CommercialOfferSnapshot] = []

    for index, person_id in enumerate(data.person_ids):
        bootstrap = get_planning_bootstrap(
            session,
            person_id=person_id,
            scheduled_at=data.scheduled_at,
            ensure_state=True,
        )
        if bootstrap.family_id != family.id:
            raise SharedPracticalRecommendationApiError(
                "All selected Persons must belong to this Family."
            )
        state_read = bootstrap.daily_nutrition_state
        if state_read is None:
            raise SharedPracticalRecommendationApiError(
                "Daily nutrition state could not be prepared for a selected Person."
            )
        if bootstrap.planning_date != data.planning_date:
            raise SharedPracticalRecommendationApiError(
                "planning_date must match every selected Person's local planning date."
            )

        person, state, candidates = load_recommendation_inputs(
            session,
            person_id=person_id,
            daily_nutrition_state_id=state_read.id,
            planning_date=data.planning_date,
            candidates=data.candidates,
        )
        if person.family_id != family.id:
            raise SharedPracticalRecommendationApiError(
                "All selected Persons must belong to this Family."
            )

        if index == 0:
            first_candidates = candidates
            practical_data = PracticalMealRecommendationCreate(
                daily_nutrition_state_id=state_read.id,
                planning_date=data.planning_date,
                scheduled_at=data.scheduled_at,
                meal_type=data.meal_type,
                candidates=data.candidates,
                location=data.location,
                available_minutes=data.available_minutes,
                has_kitchen=data.has_kitchen,
                source_kinds=data.source_kinds,
            )
            channels, offers = _build_practical_channels(
                session,
                family_id=family.id,
                candidates=candidates,
                data=practical_data,
            )
            practical_profiles = _merge_source_channels(candidates, channels)

        loaded.append((person, state))

    if first_candidates is None or practical_profiles is None:
        raise SharedPracticalRecommendationApiError(
            "Shared recommendation requires at least two selected Persons."
        )

    contexts = tuple(
        SharedMealParticipantContext(
            person=person,
            daily_state=state,
            preferences=tuple(person.food_preferences),
            adverse_reactions=tuple(person.food_adverse_reactions),
            constraints=tuple(person.nutrition_constraints),
            practical_context=PracticalMealContext(
                scheduled_at=data.scheduled_at,
                location=data.location,
                available_minutes=data.available_minutes,
                has_kitchen=data.has_kitchen,
                schedule_entries=tuple(person.schedule_entries),
            ),
            practical_profiles=practical_profiles,
        )
        for person, state in loaded
    )
    result = recommend_shared_family_meals(
        participants=contexts,
        proposals=_candidate_proposals(first_candidates, data.person_ids),
        planning_date=data.planning_date,
        engine_version="shared-family-practical-v1",
    )
    return result, offers


def create_shared_practical_recommendation(
    session: Session,
    *,
    family: Family,
    data: SharedPracticalRecommendationCreate,
) -> SharedPracticalRecommendationRead:
    result, offers = _compute_shared_recommendation(session, family=family, data=data)
    return _result_read(family, data, result, offers)


def plan_shared_practical_recommendation(
    session: Session,
    *,
    family: Family,
    data: SharedPracticalPlanCreate,
) -> SharedPracticalPlanRead:
    request = SharedPracticalRecommendationCreate(
        person_ids=data.person_ids,
        planning_date=data.planning_date,
        scheduled_at=data.scheduled_at,
        meal_type=data.meal_type,
        candidates=data.candidates,
        location=data.location,
        available_minutes=data.available_minutes,
        has_kitchen=data.has_kitchen,
        source_kinds=data.source_kinds,
    )
    result, _ = _compute_shared_recommendation(session, family=family, data=request)
    planned = materialize_shared_family_recommendation(
        session,
        recommendation=result,
        candidate_key=data.candidate_key,
        scheduled_at=data.scheduled_at,
        timezone=family.timezone,
        meal_type=data.meal_type,
        title=data.title,
        location=data.location,
        notes=data.notes,
    )
    session.flush()

    if planned.meal_event.id is None:
        raise SharedPracticalRecommendationApiError("Shared MealEvent was not persisted.")
    serving_ids: list[uuid.UUID] = []
    person_ids: list[uuid.UUID] = []
    for participant in planned.participants:
        if participant.person.id is None or participant.serving.id is None:
            raise SharedPracticalRecommendationApiError(
                "Shared recommendation participants were not fully persisted."
            )
        person_ids.append(participant.person.id)
        serving_ids.append(participant.serving.id)

    response = SharedPracticalPlanRead(
        meal_event_id=planned.meal_event.id,
        status=planned.meal_event.status,
        candidate_key=planned.selected_evaluation.candidate_key,
        person_ids=person_ids,
        serving_ids=serving_ids,
    )
    session.commit()
    return response
