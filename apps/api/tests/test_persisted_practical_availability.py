from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.models.daily_nutrition_state import DailyNutritionState
from app.models.family import Family
from app.models.food_catalog import FoodCompositionSnapshot, FoodItem
from app.models.meal_candidate_availability import MealCandidateAvailability
from app.services.meal_recommendation import MealCandidate, build_food_candidate
from app.services.persisted_practical_availability import (
    PersistedPracticalAvailabilityError,
    build_persisted_practical_profiles,
)
from app.services.recommendation_practical_context import (
    PracticalMealContext,
    recommend_meals_with_practical_context,
)

PLANNING_DATE = date(2026, 8, 22)


def _persisted_candidate(
    db_session: Session,
    family: Family,
    *,
    key: str = "food:pasta",
) -> MealCandidate:
    item = FoodItem(
        family=family,
        catalog_key=key,
        name="Pasta",
        food_kind="dish",
        source="test",
    )
    composition = FoodCompositionSnapshot(
        food_item=item,
        reference_quantity=Decimal("100.0000"),
        reference_unit="g",
        energy_kcal=Decimal("400.0000"),
        data_version="test-v1",
        source="test",
        effective_at=datetime(2026, 8, 21, tzinfo=UTC),
    )
    db_session.add(item)
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
    source_kind: str,
    source_key: str,
    location: str | None,
    preparation_minutes: int | None,
    requires_kitchen: bool,
    is_available: bool = True,
) -> None:
    if family.id is None or candidate.food_item is None or candidate.food_item.id is None:
        raise AssertionError("Availability fixtures must be persisted.")
    db_session.add(
        MealCandidateAvailability(
            family_id=family.id,
            food_item_id=candidate.food_item.id,
            candidate_kind="food_item",
            source_kind=source_kind,
            source_key=source_key,
            location=location,
            preparation_minutes=preparation_minutes,
            requires_kitchen=requires_kitchen,
            is_available=is_available,
            source="test",
        )
    )
    db_session.flush()


def _daily_state() -> DailyNutritionState:
    return DailyNutritionState(
        state_date=PLANNING_DATE,
        timezone="Europe/Lisbon",
        energy_consumed_kcal=Decimal("1000.00"),
        energy_planned_kcal=Decimal("0.00"),
        energy_remaining_min_kcal=Decimal("400.00"),
        energy_remaining_max_kcal=Decimal("600.00"),
        calculation_version="test-v1",
    )


def test_profiles_aggregate_available_sources_for_one_family(db_session: Session) -> None:
    family = Family(name="Availability Family", timezone="Europe/Lisbon")
    db_session.add(family)
    db_session.flush()
    candidate = _persisted_candidate(db_session, family)
    _availability(
        db_session,
        family,
        candidate,
        source_kind="home",
        source_key="home-kitchen",
        location="Home",
        preparation_minutes=25,
        requires_kitchen=True,
    )
    _availability(
        db_session,
        family,
        candidate,
        source_kind="delivery",
        source_key="delivery:pasta",
        location="Office",
        preparation_minutes=15,
        requires_kitchen=False,
    )

    if family.id is None:
        raise AssertionError("Family must be persisted.")
    profiles = build_persisted_practical_profiles(
        db_session,
        family_id=family.id,
        candidates=[candidate],
    )

    assert len(profiles) == 1
    profile = profiles[0]
    assert profile.is_available is True
    assert profile.available_locations == frozenset({"Home", "Office"})
    assert profile.preparation_minutes == 15
    assert profile.requires_kitchen is False


def test_source_kind_filter_builds_delivery_only_profile(db_session: Session) -> None:
    family = Family(name="Delivery Family", timezone="Europe/Lisbon")
    db_session.add(family)
    db_session.flush()
    candidate = _persisted_candidate(db_session, family, key="food:delivery-pasta")
    _availability(
        db_session,
        family,
        candidate,
        source_kind="home",
        source_key="home",
        location="Home",
        preparation_minutes=30,
        requires_kitchen=True,
    )
    _availability(
        db_session,
        family,
        candidate,
        source_kind="delivery",
        source_key="delivery",
        location="Office",
        preparation_minutes=12,
        requires_kitchen=False,
    )

    if family.id is None:
        raise AssertionError("Family must be persisted.")
    profile = build_persisted_practical_profiles(
        db_session,
        family_id=family.id,
        candidates=[candidate],
        availability_kinds=frozenset({"delivery"}),
    )[0]

    assert profile.is_available is True
    assert profile.available_locations == frozenset({"Office"})
    assert profile.preparation_minutes == 12
    assert profile.requires_kitchen is False


def test_explicitly_unavailable_source_kind_excludes_candidate(db_session: Session) -> None:
    family = Family(name="Unavailable Delivery Family", timezone="Europe/Lisbon")
    db_session.add(family)
    db_session.flush()
    candidate = _persisted_candidate(db_session, family, key="food:not-deliverable")
    _availability(
        db_session,
        family,
        candidate,
        source_kind="home",
        source_key="home",
        location="Home",
        preparation_minutes=20,
        requires_kitchen=True,
    )
    _availability(
        db_session,
        family,
        candidate,
        source_kind="delivery",
        source_key="delivery",
        location="Home",
        preparation_minutes=10,
        requires_kitchen=False,
        is_available=False,
    )

    if family.id is None:
        raise AssertionError("Family must be persisted.")
    profiles = build_persisted_practical_profiles(
        db_session,
        family_id=family.id,
        candidates=[candidate],
        availability_kinds=frozenset({"delivery"}),
    )
    result = recommend_meals_with_practical_context(
        daily_state=_daily_state(),
        candidates=[candidate],
        preferences=[],
        adverse_reactions=[],
        constraints=[],
        planning_date=PLANNING_DATE,
        practical_context=PracticalMealContext(
            scheduled_at=datetime(2026, 8, 22, 12, 30, tzinfo=UTC),
        ),
        practical_profiles=profiles,
    )

    assert result.eligible == ()
    assert result.evaluations[0].exclusion_reasons == ("candidate_unavailable",)


def test_candidate_without_persisted_availability_remains_unknown(db_session: Session) -> None:
    family = Family(name="Unknown Availability Family", timezone="Europe/Lisbon")
    db_session.add(family)
    db_session.flush()
    candidate = _persisted_candidate(db_session, family, key="food:unknown")

    if family.id is None:
        raise AssertionError("Family must be persisted.")
    profiles = build_persisted_practical_profiles(
        db_session,
        family_id=family.id,
        candidates=[candidate],
    )

    assert profiles == ()


def test_availability_lookup_rejects_candidate_from_another_family(
    db_session: Session,
) -> None:
    first = Family(name="First Family", timezone="Europe/Lisbon")
    second = Family(name="Second Family", timezone="Europe/Lisbon")
    db_session.add_all([first, second])
    db_session.flush()
    candidate = _persisted_candidate(db_session, first, key="food:first-family")

    if second.id is None:
        raise AssertionError("Family must be persisted.")
    with pytest.raises(PersistedPracticalAvailabilityError, match="another Family"):
        build_persisted_practical_profiles(
            db_session,
            family_id=second.id,
            candidates=[candidate],
        )


def test_availability_lookup_rejects_unknown_source_kind(db_session: Session) -> None:
    family = Family(name="Kind Validation Family", timezone="Europe/Lisbon")
    db_session.add(family)
    db_session.flush()
    candidate = _persisted_candidate(db_session, family, key="food:kind-validation")

    if family.id is None:
        raise AssertionError("Family must be persisted.")
    with pytest.raises(PersistedPracticalAvailabilityError, match="Unsupported availability kinds"):
        build_persisted_practical_profiles(
            db_session,
            family_id=family.id,
            candidates=[candidate],
            availability_kinds=frozenset({"teleport"}),
        )
