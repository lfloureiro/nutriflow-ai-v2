from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.family import Family
from app.models.meal_candidate_availability import (
    MealCandidateAvailability,
    MealCommercialOffer,
)
from app.models.meal_menu_snapshot import MealMenuSnapshot
from app.schemas.external_menu import ExternalMenuItemObservationWrite
from app.services.external_menu_ingestion import ingest_external_menu_item
from app.services.meal_menu_rotation import (
    learn_weekday_menu_pattern,
    record_menu_snapshots,
)


def _family(db_session: Session) -> Family:
    family = Family(
        name="Família Menu Rotativo",
        timezone="Europe/Lisbon",
        meal_discovery_sources=["uber_eats"],
        delivery_address="Rua Teste, Lisboa",
    )
    db_session.add(family)
    db_session.flush()
    return family


def _observation(
    item_key: str,
    item_name: str,
    observed_at: datetime,
) -> ExternalMenuItemObservationWrite:
    return ExternalMenuItemObservationWrite(
        provider_key="uber_eats",
        provider_name="Uber Eats",
        merchant_key="rotating-merchant",
        merchant_name="Restaurante Rotativo",
        item_key=item_key,
        item_name=item_name,
        source_kind="delivery",
        location="Rua Teste, Lisboa",
        item_price=Decimal("10.00"),
        currency="EUR",
        observed_at=observed_at,
        source_reference=f"provider://uber_eats/rotating-merchant/{item_key}",
    )


def _record(
    db_session: Session,
    *,
    family: Family,
    observations: tuple[ExternalMenuItemObservationWrite, ...],
    limit: int = 80,
) -> tuple:
    ingested = tuple(
        ingest_external_menu_item(db_session, family=family, data=observation)
        for observation in observations
    )
    return record_menu_snapshots(
        db_session,
        family=family,
        provider_key="uber_eats",
        observations=observations,
        ingested=ingested,
        query="Restaurante Rotativo",
        limit=limit,
    )


def test_complete_snapshots_preserve_catalogue_and_reconcile_current_menu(
    db_session: Session,
) -> None:
    family = _family(db_session)
    first_day = datetime(2026, 8, 24, 11, 0, tzinfo=UTC)
    second_day = datetime(2026, 8, 25, 11, 0, tzinfo=UTC)
    third_day = datetime(2026, 8, 26, 11, 0, tzinfo=UTC)

    first = (
        _observation("dish-a", "Prato A", first_day),
        _observation("dish-b", "Prato B", first_day),
    )
    first_ingested = tuple(
        ingest_external_menu_item(db_session, family=family, data=item) for item in first
    )
    record_menu_snapshots(
        db_session,
        family=family,
        provider_key="uber_eats",
        observations=first,
        ingested=first_ingested,
        query="Restaurante Rotativo",
        limit=80,
    )
    dish_b_food_item_id = first_ingested[1].food_item_id
    dish_b_availability_id = first_ingested[1].availability_id
    dish_b_offer_id = first_ingested[1].offer_id

    _record(
        db_session,
        family=family,
        observations=(_observation("dish-a", "Prato A", second_day),),
    )

    dish_b_availability = db_session.get(
        MealCandidateAvailability,
        dish_b_availability_id,
    )
    dish_b_offer = db_session.get(MealCommercialOffer, dish_b_offer_id)
    assert dish_b_availability is not None
    assert dish_b_offer is not None
    assert not dish_b_availability.is_available
    assert not dish_b_offer.is_available

    third_observation = _observation("dish-b", "Prato B", third_day)
    third_ingested = (
        ingest_external_menu_item(
            db_session,
            family=family,
            data=third_observation,
        ),
    )
    record_menu_snapshots(
        db_session,
        family=family,
        provider_key="uber_eats",
        observations=(third_observation,),
        ingested=third_ingested,
        query="Restaurante Rotativo",
        limit=80,
    )

    assert third_ingested[0].food_item_id == dish_b_food_item_id
    assert third_ingested[0].availability_id == dish_b_availability_id
    db_session.refresh(dish_b_availability)
    db_session.refresh(dish_b_offer)
    assert dish_b_availability.is_available
    assert dish_b_offer.is_available
    snapshots = db_session.scalars(
        select(MealMenuSnapshot).where(MealMenuSnapshot.family_id == family.id)
    ).all()
    assert len(snapshots) == 3


def test_incomplete_snapshot_does_not_mark_unseen_dishes_unavailable(
    db_session: Session,
) -> None:
    family = _family(db_session)
    first_day = datetime(2026, 8, 24, 11, 0, tzinfo=UTC)
    second_day = datetime(2026, 8, 25, 11, 0, tzinfo=UTC)

    first = (
        _observation("dish-a", "Prato A", first_day),
        _observation("dish-b", "Prato B", first_day),
    )
    first_ingested = tuple(
        ingest_external_menu_item(db_session, family=family, data=item) for item in first
    )
    record_menu_snapshots(
        db_session,
        family=family,
        provider_key="uber_eats",
        observations=first,
        ingested=first_ingested,
        query="Restaurante Rotativo",
        limit=80,
    )

    dish_b_availability = db_session.get(
        MealCandidateAvailability,
        first_ingested[1].availability_id,
    )
    assert dish_b_availability is not None

    _record(
        db_session,
        family=family,
        observations=(_observation("dish-a", "Prato A", second_day),),
        limit=1,
    )

    db_session.refresh(dish_b_availability)
    assert dish_b_availability.is_available


def test_weekday_pattern_uses_union_of_complete_snapshots_per_calendar_day(
    db_session: Session,
) -> None:
    family = _family(db_session)
    monday_1_morning = datetime(2026, 8, 24, 9, 0, tzinfo=UTC)
    monday_1_later = datetime(2026, 8, 24, 12, 0, tzinfo=UTC)
    monday_2 = datetime(2026, 8, 31, 11, 0, tzinfo=UTC)

    _record(
        db_session,
        family=family,
        observations=(
            _observation("dish-a", "Prato A", monday_1_morning),
            _observation("dish-b", "Prato B", monday_1_morning),
        ),
    )
    # Same local day, later snapshot after Prato B sold out. Learning must remember
    # that Prato B was offered on this Monday rather than replacing the day's menu.
    _record(
        db_session,
        family=family,
        observations=(_observation("dish-a", "Prato A", monday_1_later),),
    )
    _record(
        db_session,
        family=family,
        observations=(
            _observation("dish-a", "Prato A", monday_2),
            _observation("dish-b", "Prato B", monday_2),
        ),
    )

    patterns = learn_weekday_menu_pattern(
        db_session,
        family_id=family.id,
        provider_key="uber_eats",
        merchant_key="rotating-merchant",
    )
    by_name = {pattern.item_name: pattern for pattern in patterns}

    assert by_name["Prato A"].weekday == 0
    assert by_name["Prato A"].sampled_days == 2
    assert by_name["Prato A"].observed_days == 2
    assert by_name["Prato A"].frequency == Decimal("1.000")
    assert by_name["Prato B"].sampled_days == 2
    assert by_name["Prato B"].observed_days == 2
    assert by_name["Prato B"].frequency == Decimal("1.000")
