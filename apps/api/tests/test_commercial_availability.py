from datetime import UTC, date, datetime, time
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.models.family import Family
from app.models.food_catalog import FoodCompositionSnapshot, FoodItem
from app.models.meal_candidate_availability import (
    MealCandidateAvailability,
    MealCommercialOffer,
    MealSourceOpeningWindow,
)
from app.services.commercial_availability import (
    CommercialAvailabilityError,
    build_commercial_planning_context,
)
from app.services.meal_recommendation import MealCandidate, build_food_candidate

PLANNING_AT = datetime(2026, 8, 21, 12, 30, tzinfo=UTC)


def _family(db_session: Session, name: str = "Commercial Family") -> Family:
    family = Family(name=name, timezone="Europe/Lisbon")
    db_session.add(family)
    db_session.flush()
    return family


def _candidate(
    db_session: Session,
    family: Family,
    *,
    key: str = "food:commercial-pasta",
) -> MealCandidate:
    item = FoodItem(
        family=family,
        catalog_key=key,
        name="Commercial pasta",
        food_kind="dish",
        source="test",
    )
    composition = FoodCompositionSnapshot(
        food_item=item,
        reference_quantity=Decimal("100.0000"),
        reference_unit="g",
        energy_kcal=Decimal("350.0000"),
        data_version="test-v1",
        source="test",
        effective_at=datetime(2026, 8, 20, tzinfo=UTC),
    )
    db_session.add(composition)
    db_session.flush()
    return build_food_candidate(
        composition,
        quantity=Decimal("100.0000"),
        quantity_unit="g",
    )


def _availability(
    db_session: Session,
    family: Family,
    candidate: MealCandidate,
    *,
    source_kind: str = "delivery",
    source_key: str = "delivery:pasta",
    location: str | None = "Office",
    preparation_minutes: int | None = 20,
    is_available: bool = True,
) -> MealCandidateAvailability:
    if family.id is None or candidate.food_item is None or candidate.food_item.id is None:
        raise AssertionError("Commercial fixtures must be persisted.")
    availability = MealCandidateAvailability(
        family_id=family.id,
        food_item_id=candidate.food_item.id,
        candidate_kind="food_item",
        source_kind=source_kind,
        source_key=source_key,
        location=location,
        preparation_minutes=preparation_minutes,
        requires_kitchen=False,
        is_available=is_available,
        source="test",
    )
    db_session.add(availability)
    db_session.flush()
    return availability


def _opening_window(
    db_session: Session,
    availability: MealCandidateAvailability,
    *,
    weekday: int,
    start: time,
    end: time,
    timezone: str = "UTC",
    valid_from: date | None = None,
    valid_until: date | None = None,
) -> MealSourceOpeningWindow:
    if availability.id is None:
        raise AssertionError("Availability must be persisted.")
    window = MealSourceOpeningWindow(
        availability_id=availability.id,
        weekday=weekday,
        local_start_time=start,
        local_end_time=end,
        timezone=timezone,
        valid_from=valid_from,
        valid_until=valid_until,
        source="test",
        observed_at=PLANNING_AT,
    )
    db_session.add(window)
    db_session.flush()
    return window


def _offer(
    db_session: Session,
    family: Family,
    availability: MealCandidateAvailability,
    *,
    offer_key: str,
    provider_key: str,
    item_price: str,
    currency: str = "EUR",
    delivery_fee: str | None = None,
    minimum_order: str | None = None,
    valid_from: datetime | None = None,
    valid_until: datetime | None = None,
    is_available: bool = True,
) -> MealCommercialOffer:
    if family.id is None or availability.id is None:
        raise AssertionError("Commercial offer fixtures must be persisted.")
    offer = MealCommercialOffer(
        family_id=family.id,
        availability_id=availability.id,
        offer_key=offer_key,
        provider_key=provider_key,
        provider_name=provider_key.title(),
        item_price=Decimal(item_price),
        currency=currency,
        delivery_fee=Decimal(delivery_fee) if delivery_fee is not None else None,
        minimum_order=Decimal(minimum_order) if minimum_order is not None else None,
        is_available=is_available,
        valid_from=valid_from,
        valid_until=valid_until,
        observed_at=PLANNING_AT,
        source="test",
        source_reference=f"ref:{offer_key}",
    )
    db_session.add(offer)
    db_session.flush()
    return offer


def test_open_delivery_source_returns_practical_profile_and_price(
    db_session: Session,
) -> None:
    family = _family(db_session)
    candidate = _candidate(db_session, family)
    availability = _availability(db_session, family, candidate)
    _opening_window(
        db_session,
        availability,
        weekday=4,
        start=time(11, 0),
        end=time(22, 0),
    )
    _offer(
        db_session,
        family,
        availability,
        offer_key="offer:pasta",
        provider_key="provider-a",
        item_price="12.50",
        delivery_fee="2.00",
        minimum_order="15.00",
    )

    if family.id is None:
        raise AssertionError("Family must be persisted.")
    result = build_commercial_planning_context(
        db_session,
        family_id=family.id,
        candidates=[candidate],
        scheduled_at=PLANNING_AT,
    )

    assert result.practical_profiles[0].is_available is True
    assert result.practical_profiles[0].available_locations == frozenset({"Office"})
    assert result.practical_profiles[0].preparation_minutes == 20
    assert len(result.offers) == 1
    assert result.offers[0].currency == "EUR"
    assert result.offers[0].total_known_price == Decimal("14.50")
    assert result.offers[0].minimum_order == Decimal("15.00")


def test_closed_modeled_source_is_explicitly_unavailable(db_session: Session) -> None:
    family = _family(db_session, "Closed Source Family")
    candidate = _candidate(db_session, family, key="food:closed")
    availability = _availability(db_session, family, candidate, source_key="delivery:closed")
    _opening_window(
        db_session,
        availability,
        weekday=4,
        start=time(18, 0),
        end=time(22, 0),
    )
    _offer(
        db_session,
        family,
        availability,
        offer_key="offer:closed",
        provider_key="provider-closed",
        item_price="10.00",
    )

    if family.id is None:
        raise AssertionError("Family must be persisted.")
    result = build_commercial_planning_context(
        db_session,
        family_id=family.id,
        candidates=[candidate],
        scheduled_at=PLANNING_AT,
    )

    assert result.practical_profiles[0].is_available is False
    assert result.offers == ()


def test_overnight_opening_window_uses_the_day_the_window_starts(
    db_session: Session,
) -> None:
    family = _family(db_session, "Overnight Family")
    candidate = _candidate(db_session, family, key="food:overnight")
    availability = _availability(
        db_session,
        family,
        candidate,
        source_kind="restaurant",
        source_key="restaurant:overnight",
    )
    _opening_window(
        db_session,
        availability,
        weekday=4,
        start=time(22, 0),
        end=time(2, 0),
        valid_from=date(2026, 8, 1),
        valid_until=date(2026, 8, 31),
    )

    if family.id is None:
        raise AssertionError("Family must be persisted.")
    result = build_commercial_planning_context(
        db_session,
        family_id=family.id,
        candidates=[candidate],
        scheduled_at=datetime(2026, 8, 22, 1, 0, tzinfo=UTC),
        source_kinds=frozenset({"restaurant"}),
    )

    assert result.practical_profiles[0].is_available is True


def test_missing_opening_windows_preserves_unknown_opening_hours(
    db_session: Session,
) -> None:
    family = _family(db_session, "Unknown Hours Family")
    candidate = _candidate(db_session, family, key="food:unknown-hours")
    availability = _availability(
        db_session,
        family,
        candidate,
        source_key="delivery:unknown-hours",
    )
    _offer(
        db_session,
        family,
        availability,
        offer_key="offer:unknown-hours",
        provider_key="provider-unknown",
        item_price="9.00",
    )

    if family.id is None:
        raise AssertionError("Family must be persisted.")
    result = build_commercial_planning_context(
        db_session,
        family_id=family.id,
        candidates=[candidate],
        scheduled_at=PLANNING_AT,
    )

    assert result.practical_profiles[0].is_available is True
    assert len(result.offers) == 1


def test_offer_validity_does_not_make_an_open_source_unavailable(
    db_session: Session,
) -> None:
    family = _family(db_session, "Offer Validity Family")
    candidate = _candidate(db_session, family, key="food:offer-validity")
    availability = _availability(
        db_session,
        family,
        candidate,
        source_key="delivery:offer-validity",
    )
    _offer(
        db_session,
        family,
        availability,
        offer_key="offer:expired",
        provider_key="provider-expired",
        item_price="8.00",
        valid_until=PLANNING_AT,
    )
    _offer(
        db_session,
        family,
        availability,
        offer_key="offer:future",
        provider_key="provider-future",
        item_price="7.00",
        valid_from=datetime(2026, 8, 21, 13, 0, tzinfo=UTC),
    )

    if family.id is None:
        raise AssertionError("Family must be persisted.")
    result = build_commercial_planning_context(
        db_session,
        family_id=family.id,
        candidates=[candidate],
        scheduled_at=PLANNING_AT,
    )

    assert result.practical_profiles[0].is_available is True
    assert result.offers == ()


def test_offers_are_sorted_deterministically_without_currency_conversion(
    db_session: Session,
) -> None:
    family = _family(db_session, "Currency Family")
    candidate = _candidate(db_session, family, key="food:currency")
    availability = _availability(
        db_session,
        family,
        candidate,
        source_key="delivery:currency",
    )
    _offer(
        db_session,
        family,
        availability,
        offer_key="offer:eur-expensive",
        provider_key="provider-b",
        item_price="10.00",
        delivery_fee="1.00",
    )
    _offer(
        db_session,
        family,
        availability,
        offer_key="offer:eur-cheap",
        provider_key="provider-a",
        item_price="8.00",
        delivery_fee="1.00",
    )
    _offer(
        db_session,
        family,
        availability,
        offer_key="offer:usd",
        provider_key="provider-c",
        item_price="5.00",
        currency="USD",
    )

    if family.id is None:
        raise AssertionError("Family must be persisted.")
    result = build_commercial_planning_context(
        db_session,
        family_id=family.id,
        candidates=[candidate],
        scheduled_at=PLANNING_AT,
    )

    assert [offer.offer_key for offer in result.offers] == [
        "offer:eur-cheap",
        "offer:eur-expensive",
        "offer:usd",
    ]


def test_commercial_lookup_enforces_family_and_source_kind_boundaries(
    db_session: Session,
) -> None:
    first = _family(db_session, "First Commercial Family")
    second = _family(db_session, "Second Commercial Family")
    candidate = _candidate(db_session, first, key="food:first-commercial")

    if second.id is None:
        raise AssertionError("Family must be persisted.")
    with pytest.raises(CommercialAvailabilityError, match="another Family"):
        build_commercial_planning_context(
            db_session,
            family_id=second.id,
            candidates=[candidate],
            scheduled_at=PLANNING_AT,
        )

    if first.id is None:
        raise AssertionError("Family must be persisted.")
    with pytest.raises(CommercialAvailabilityError, match="Unsupported commercial source kinds"):
        build_commercial_planning_context(
            db_session,
            family_id=first.id,
            candidates=[candidate],
            scheduled_at=PLANNING_AT,
            source_kinds=frozenset({"home"}),
        )
