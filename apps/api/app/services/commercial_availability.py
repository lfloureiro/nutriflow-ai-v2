import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.meal_candidate_availability import (
    COMMERCIAL_AVAILABILITY_KINDS,
    MealCandidateAvailability,
    MealCommercialOffer,
    MealSourceOpeningWindow,
)
from app.services.meal_recommendation import MealCandidate
from app.services.recommendation_practical_context import CandidatePracticalProfile

ZERO = Decimal(0)
DEFAULT_COMMERCIAL_SOURCE_KINDS = frozenset({"restaurant", "delivery"})


class CommercialAvailabilityError(ValueError):
    pass


@dataclass(frozen=True)
class CommercialOfferSnapshot:
    candidate_key: str
    source_kind: str
    source_key: str
    location: str | None
    offer_key: str
    provider_key: str
    provider_name: str | None
    item_price: Decimal
    currency: str
    delivery_fee: Decimal | None
    minimum_order: Decimal | None
    observed_at: datetime
    source_reference: str | None

    @property
    def total_known_price(self) -> Decimal:
        return self.item_price + (self.delivery_fee or ZERO)


@dataclass(frozen=True)
class CommercialPlanningResult:
    practical_profiles: tuple[CandidatePracticalProfile, ...]
    offers: tuple[CommercialOfferSnapshot, ...]


def _is_timezone_aware(value: datetime) -> bool:
    return value.tzinfo is not None and value.utcoffset() is not None


def _validate_scheduled_at(scheduled_at: datetime) -> None:
    if not _is_timezone_aware(scheduled_at):
        raise CommercialAvailabilityError("scheduled_at must be timezone-aware.")


def _validated_source_kinds(source_kinds: frozenset[str]) -> frozenset[str]:
    if not source_kinds:
        raise CommercialAvailabilityError("source_kinds must contain at least one source kind.")
    unsupported = source_kinds - COMMERCIAL_AVAILABILITY_KINDS
    if unsupported:
        raise CommercialAvailabilityError(
            "Unsupported commercial source kinds: " + ", ".join(sorted(unsupported)) + "."
        )
    return source_kinds


def _candidate_identity(
    candidate: MealCandidate,
    *,
    family_id: uuid.UUID,
) -> tuple[str, uuid.UUID]:
    if candidate.food_item is not None:
        if candidate.food_item.id is None:
            raise CommercialAvailabilityError(
                f"Food candidate {candidate.key!r} must be persisted before commercial lookup."
            )
        if candidate.food_item.family_id not in {None, family_id}:
            raise CommercialAvailabilityError(
                f"Food candidate {candidate.key!r} belongs to another Family."
            )
        return "food_item", candidate.food_item.id

    if candidate.recipe is not None:
        if candidate.recipe.id is None:
            raise CommercialAvailabilityError(
                f"Recipe candidate {candidate.key!r} must be persisted before commercial lookup."
            )
        if candidate.recipe.family_id not in {None, family_id}:
            raise CommercialAvailabilityError(
                f"Recipe candidate {candidate.key!r} belongs to another Family."
            )
        return "recipe", candidate.recipe.id

    raise CommercialAvailabilityError(
        f"Candidate {candidate.key!r} has no persisted FoodItem or Recipe identity."
    )


def _window_occurrence_date(
    window: MealSourceOpeningWindow,
    scheduled_at: datetime,
):
    try:
        zone = ZoneInfo(window.timezone)
    except ZoneInfoNotFoundError as exc:
        raise CommercialAvailabilityError(
            f"Unknown timezone on commercial opening window: {window.timezone!r}."
        ) from exc

    local_at = scheduled_at.astimezone(zone)
    local_time = local_at.timetz().replace(tzinfo=None)
    start = window.local_start_time
    end = window.local_end_time

    if start == end:
        occurrence_date = local_at.date()
    elif start < end:
        if not start <= local_time < end:
            return None
        occurrence_date = local_at.date()
    else:
        if local_time >= start:
            occurrence_date = local_at.date()
        elif local_time < end:
            occurrence_date = local_at.date() - timedelta(days=1)
        else:
            return None

    if occurrence_date.weekday() != window.weekday:
        return None
    if window.valid_from is not None and occurrence_date < window.valid_from:
        return None
    if window.valid_until is not None and occurrence_date > window.valid_until:
        return None
    return occurrence_date


def _source_is_open(
    availability: MealCandidateAvailability,
    scheduled_at: datetime,
) -> bool | None:
    if not availability.opening_windows:
        return None
    return any(
        _window_occurrence_date(window, scheduled_at) is not None
        for window in availability.opening_windows
    )


def _offer_is_active(
    offer: MealCommercialOffer,
    *,
    family_id: uuid.UUID,
    scheduled_at: datetime,
) -> bool:
    if offer.family_id != family_id:
        raise CommercialAvailabilityError(
            f"Commercial offer {offer.offer_key!r} belongs to another Family."
        )
    if not _is_timezone_aware(offer.observed_at):
        raise CommercialAvailabilityError(
            f"Commercial offer {offer.offer_key!r} has a non-timezone-aware observed_at."
        )
    if not offer.is_available:
        return False
    if offer.valid_from is not None and scheduled_at < offer.valid_from:
        return False
    return offer.valid_until is None or scheduled_at < offer.valid_until


def _profile_from_sources(
    candidate_key: str,
    sources: list[MealCandidateAvailability],
    scheduled_at: datetime,
) -> tuple[CandidatePracticalProfile, list[MealCandidateAvailability]]:
    usable = [
        source
        for source in sources
        if source.is_available and _source_is_open(source, scheduled_at) is not False
    ]
    if not usable:
        return CandidatePracticalProfile(candidate_key=candidate_key, is_available=False), []

    preparation_minutes = min(
        (
            source.preparation_minutes
            for source in usable
            if source.preparation_minutes is not None
        ),
        default=None,
    )
    available_locations: frozenset[str] | None = None
    if all(source.location for source in usable):
        available_locations = frozenset(
            source.location for source in usable if source.location is not None
        )

    return (
        CandidatePracticalProfile(
            candidate_key=candidate_key,
            is_available=True,
            available_locations=available_locations,
            preparation_minutes=preparation_minutes,
            requires_kitchen=all(source.requires_kitchen for source in usable),
        ),
        usable,
    )


def _offer_snapshot(
    candidate_key: str,
    source: MealCandidateAvailability,
    offer: MealCommercialOffer,
) -> CommercialOfferSnapshot:
    currency = offer.currency.upper()
    if len(currency) != 3:
        raise CommercialAvailabilityError(
            f"Commercial offer {offer.offer_key!r} has an invalid currency code."
        )
    return CommercialOfferSnapshot(
        candidate_key=candidate_key,
        source_kind=source.source_kind,
        source_key=source.source_key,
        location=source.location,
        offer_key=offer.offer_key,
        provider_key=offer.provider_key,
        provider_name=offer.provider_name,
        item_price=offer.item_price,
        currency=currency,
        delivery_fee=offer.delivery_fee,
        minimum_order=offer.minimum_order,
        observed_at=offer.observed_at,
        source_reference=offer.source_reference,
    )


def build_commercial_planning_context(
    session: Session,
    *,
    family_id: uuid.UUID,
    candidates: list[MealCandidate],
    scheduled_at: datetime,
    source_kinds: frozenset[str] = DEFAULT_COMMERCIAL_SOURCE_KINDS,
) -> CommercialPlanningResult:
    _validate_scheduled_at(scheduled_at)
    requested_kinds = _validated_source_kinds(source_kinds)
    if not candidates:
        return CommercialPlanningResult(practical_profiles=(), offers=())

    candidate_keys = [candidate.key for candidate in candidates]
    if len(candidate_keys) != len(set(candidate_keys)):
        raise CommercialAvailabilityError("Candidate keys must be unique for commercial lookup.")

    identities = {
        candidate.key: _candidate_identity(candidate, family_id=family_id)
        for candidate in candidates
    }
    food_ids = [identity for kind, identity in identities.values() if kind == "food_item"]
    recipe_ids = [identity for kind, identity in identities.values() if kind == "recipe"]

    filters = []
    if food_ids:
        filters.append(MealCandidateAvailability.food_item_id.in_(food_ids))
    if recipe_ids:
        filters.append(MealCandidateAvailability.recipe_id.in_(recipe_ids))

    rows = session.scalars(
        select(MealCandidateAvailability)
        .where(
            MealCandidateAvailability.family_id == family_id,
            MealCandidateAvailability.source_kind.in_(requested_kinds),
            or_(*filters),
        )
        .options(
            selectinload(MealCandidateAvailability.opening_windows),
            selectinload(MealCandidateAvailability.commercial_offers),
        )
        .order_by(
            MealCandidateAvailability.candidate_kind,
            MealCandidateAvailability.source_key,
            MealCandidateAvailability.id,
        )
    ).all()

    grouped: dict[tuple[str, uuid.UUID], list[MealCandidateAvailability]] = defaultdict(list)
    for row in rows:
        if row.candidate_kind == "food_item" and row.food_item_id is not None:
            grouped[("food_item", row.food_item_id)].append(row)
        elif row.candidate_kind == "recipe" and row.recipe_id is not None:
            grouped[("recipe", row.recipe_id)].append(row)

    profiles: list[CandidatePracticalProfile] = []
    offers: list[CommercialOfferSnapshot] = []
    for candidate in candidates:
        candidate_sources = grouped.get(identities[candidate.key], [])
        if not candidate_sources:
            continue

        profile, usable_sources = _profile_from_sources(
            candidate.key,
            candidate_sources,
            scheduled_at,
        )
        profiles.append(profile)
        for source in usable_sources:
            for offer in source.commercial_offers:
                if _offer_is_active(
                    offer,
                    family_id=family_id,
                    scheduled_at=scheduled_at,
                ):
                    offers.append(_offer_snapshot(candidate.key, source, offer))

    offers.sort(
        key=lambda offer: (
            offer.candidate_key,
            offer.currency,
            offer.total_known_price,
            offer.provider_key,
            offer.offer_key,
        )
    )
    return CommercialPlanningResult(
        practical_profiles=tuple(profiles),
        offers=tuple(offers),
    )
