import uuid
from collections.abc import Iterable
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.orm import Session

from app.schemas.practical_recommendation import (
    CommercialOfferRead,
    PracticalMealRecommendationCreate,
    PracticalMealRecommendationRunRead,
)
from app.services.commercial_availability import (
    CommercialAvailabilityError,
    CommercialOfferSnapshot,
    build_commercial_planning_context,
)
from app.services.meal_recommendation import MealCandidate
from app.services.meal_recommendation_api import (
    load_recommendation_inputs,
    persist_recommendation_response,
)
from app.services.pantry_planning import PantryPlanningError, build_pantry_stock_practical_profiles
from app.services.persisted_practical_availability import (
    PersistedPracticalAvailabilityError,
    build_persisted_practical_profiles,
)
from app.services.recipe_preference import load_family_recipe_ratings
from app.services.recommendation_practical_context import (
    CandidatePracticalProfile,
    PracticalMealContext,
    PracticalRecommendationError,
    recommend_meals_with_practical_context,
)

_COMMERCIAL_SOURCE_KINDS = frozenset({"restaurant", "delivery", "store"})


class PracticalRecommendationApiError(ValueError):
    pass


def _validate_planning_instant(
    data: PracticalMealRecommendationCreate,
    *,
    state_timezone: str,
) -> None:
    if data.scheduled_at.tzinfo is None or data.scheduled_at.utcoffset() is None:
        raise PracticalRecommendationApiError("scheduled_at must be timezone-aware.")
    try:
        zone = ZoneInfo(state_timezone)
    except ZoneInfoNotFoundError as exc:
        raise PracticalRecommendationApiError(
            f"Unknown DailyNutritionState timezone: {state_timezone!r}."
        ) from exc
    if data.scheduled_at.astimezone(zone).date() != data.planning_date:
        raise PracticalRecommendationApiError(
            "scheduled_at must fall on planning_date in the DailyNutritionState timezone."
        )


def _profile_map(
    profiles: Iterable[CandidatePracticalProfile],
) -> dict[str, CandidatePracticalProfile]:
    return {profile.candidate_key: profile for profile in profiles}


def _pantry_channel_profiles(
    candidates: list[MealCandidate],
    stock_profiles: tuple[CandidatePracticalProfile, ...],
    source_profiles: tuple[CandidatePracticalProfile, ...],
) -> tuple[CandidatePracticalProfile, ...]:
    stock_by_key = _profile_map(stock_profiles)
    source_by_key = _profile_map(source_profiles)
    combined: list[CandidatePracticalProfile] = []

    for candidate in candidates:
        stock = stock_by_key[candidate.key]
        source = source_by_key.get(candidate.key)
        if stock.is_available is False or (source is not None and source.is_available is False):
            combined.append(
                CandidatePracticalProfile(candidate_key=candidate.key, is_available=False)
            )
            continue

        if source is None:
            combined.append(stock)
            continue

        combined.append(
            CandidatePracticalProfile(
                candidate_key=candidate.key,
                is_available=stock.is_available,
                available_locations=source.available_locations,
                preparation_minutes=source.preparation_minutes,
                requires_kitchen=source.requires_kitchen,
            )
        )

    return tuple(combined)


def _merge_candidate_channels(
    candidate: MealCandidate,
    channel_maps: list[dict[str, CandidatePracticalProfile]],
) -> CandidatePracticalProfile:
    evidence = [channel.get(candidate.key) for channel in channel_maps]
    explicitly_available = [
        profile for profile in evidence if profile is not None and profile.is_available is True
    ]

    if explicitly_available:
        is_available: bool | None = True
        metadata_profiles = explicitly_available
    elif evidence and all(
        profile is not None and profile.is_available is False for profile in evidence
    ):
        is_available = False
        metadata_profiles = []
    else:
        is_available = None
        metadata_profiles = [
            profile
            for profile in evidence
            if profile is not None and profile.is_available is None
        ]

    preparation_minutes = min(
        (
            profile.preparation_minutes
            for profile in metadata_profiles
            if profile.preparation_minutes is not None
        ),
        default=None,
    )
    available_locations: frozenset[str] | None = None
    if metadata_profiles and all(
        profile.available_locations is not None for profile in metadata_profiles
    ):
        available_locations = frozenset(
            location
            for profile in metadata_profiles
            for location in (profile.available_locations or frozenset())
        )

    return CandidatePracticalProfile(
        candidate_key=candidate.key,
        is_available=is_available,
        available_locations=available_locations,
        preparation_minutes=preparation_minutes,
        requires_kitchen=bool(metadata_profiles)
        and all(profile.requires_kitchen for profile in metadata_profiles),
    )


def _merge_source_channels(
    candidates: list[MealCandidate],
    channels: list[tuple[CandidatePracticalProfile, ...]],
) -> tuple[CandidatePracticalProfile, ...]:
    channel_maps = [_profile_map(channel) for channel in channels]
    return tuple(
        _merge_candidate_channels(candidate, channel_maps)
        for candidate in candidates
    )


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


def _build_practical_channels(
    session: Session,
    *,
    family_id: uuid.UUID,
    candidates: list[MealCandidate],
    data: PracticalMealRecommendationCreate,
) -> tuple[list[tuple[CandidatePracticalProfile, ...]], list[CommercialOfferSnapshot]]:
    requested_kinds = frozenset(data.source_kinds)
    channels: list[tuple[CandidatePracticalProfile, ...]] = []
    offers: list[CommercialOfferSnapshot] = []

    if "home" in requested_kinds:
        channels.append(
            build_persisted_practical_profiles(
                session,
                family_id=family_id,
                candidates=candidates,
                availability_kinds=frozenset({"home"}),
            )
        )

    if "pantry" in requested_kinds:
        stock_profiles = build_pantry_stock_practical_profiles(
            session,
            family_id=family_id,
            candidates=candidates,
            as_of=data.scheduled_at,
        )
        pantry_source_profiles = build_persisted_practical_profiles(
            session,
            family_id=family_id,
            candidates=candidates,
            availability_kinds=frozenset({"pantry"}),
        )
        channels.append(
            _pantry_channel_profiles(candidates, stock_profiles, pantry_source_profiles)
        )

    for source_kind in sorted(requested_kinds & _COMMERCIAL_SOURCE_KINDS):
        commercial = build_commercial_planning_context(
            session,
            family_id=family_id,
            candidates=candidates,
            scheduled_at=data.scheduled_at,
            source_kinds=frozenset({source_kind}),
        )
        channels.append(commercial.practical_profiles)
        offers.extend(commercial.offers)

    offers.sort(
        key=lambda offer: (
            offer.candidate_key,
            offer.currency,
            offer.total_known_price,
            offer.provider_key,
            offer.offer_key,
        )
    )
    return channels, offers


def create_practical_meal_recommendation(
    session: Session,
    *,
    person_id: uuid.UUID,
    data: PracticalMealRecommendationCreate,
) -> PracticalMealRecommendationRunRead:
    person, state, candidates = load_recommendation_inputs(
        session,
        person_id=person_id,
        daily_nutrition_state_id=data.daily_nutrition_state_id,
        planning_date=data.planning_date,
        candidates=data.candidates,
    )
    _validate_planning_instant(data, state_timezone=state.timezone)

    try:
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
        recommendation = recommend_meals_with_practical_context(
            daily_state=state,
            candidates=candidates,
            preferences=list(person.food_preferences),
            adverse_reactions=list(person.food_adverse_reactions),
            constraints=list(person.nutrition_constraints),
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
            engine_version="meal-recommendation-practical-v2",
        )
    except (
        CommercialAvailabilityError,
        PantryPlanningError,
        PersistedPracticalAvailabilityError,
        PracticalRecommendationError,
    ) as exc:
        raise PracticalRecommendationApiError(str(exc)) from exc

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
            "candidate_composition_ids": [
                str(candidate.composition_id) for candidate in data.candidates
            ],
            "scheduled_at": data.scheduled_at.isoformat(),
            "location": data.location,
            "available_minutes": data.available_minutes,
            "has_kitchen": data.has_kitchen,
            "source_kinds": source_kinds,
            "commercial_offer_keys": [offer.offer_key for offer in offers],
            "family_recipe_ratings": {
                key: str(value) for key, value in sorted(family_recipe_ratings.items())
            },
        },
    )

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
        options=run.options,
        commercial_offers=[_commercial_offer_read(offer) for offer in offers],
    )
