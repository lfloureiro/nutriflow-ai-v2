from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.family import Family
from app.schemas.external_menu import (
    ExternalMenuItemObservationWrite,
    ExternalMenuNutritionWrite,
)
from app.services.external_menu_ingestion import ingest_external_menu_item
from app.services.meal_delivery_catalog import list_meal_delivery_menu_items

NOW = datetime(2026, 8, 24, 12, 0, tzinfo=UTC)


def _family(db_session: Session, name: str) -> Family:
    family = Family(
        name=name,
        timezone="Europe/Lisbon",
        meal_discovery_sources=["shared_recipes", "uber_eats"],
    )
    db_session.add(family)
    db_session.flush()
    return family


def _observation() -> ExternalMenuItemObservationWrite:
    return ExternalMenuItemObservationWrite(
        provider_key="uber_eats",
        provider_name="Uber Eats",
        merchant_key="merchant-1",
        merchant_name="Restaurante Teste",
        item_key="dish-1",
        item_name="Frango com arroz",
        description="Frango grelhado, arroz e legumes",
        source_kind="delivery",
        location="Benfica, Lisboa",
        item_price=Decimal("12.90"),
        currency="EUR",
        delivery_fee=Decimal("1.99"),
        minimum_order=Decimal("8.00"),
        observed_at=NOW,
        valid_until=NOW + timedelta(hours=6),
        source_reference="provider://uber_eats/merchant-1/dish-1",
        nutrition=ExternalMenuNutritionWrite(
            evidence_level="official",
            reference_quantity=Decimal(1),
            reference_unit="serving",
            energy_kcal=Decimal(610),
            nutrients=[],
        ),
    )


def test_delivery_catalog_restores_persisted_nutrition_evidence(
    db_session: Session,
) -> None:
    family = _family(db_session, "Família A")
    ingested = ingest_external_menu_item(
        db_session,
        family=family,
        data=_observation(),
    )
    db_session.flush()

    items = list_meal_delivery_menu_items(
        db_session,
        family=family,
        provider_key="uber_eats",
        at=NOW + timedelta(minutes=1),
    )

    assert len(items) == 1
    item = items[0]
    assert item.catalog_key == ingested.catalog_key
    assert item.merchant_name == "Restaurante Teste"
    assert item.item_name == "Frango com arroz"
    assert item.item_price == Decimal("12.90")
    assert item.delivery_fee == Decimal("1.99")
    assert item.minimum_order == Decimal("8.00")
    assert item.energy_kcal == Decimal("610.0000")
    assert item.nutrition_evidence_level == "official"
    assert item.nutrition_confidence is None
    assert item.eligible_for_nutrition_ranking


def test_delivery_catalog_is_family_scoped(db_session: Session) -> None:
    first_family = _family(db_session, "Família A")
    second_family = _family(db_session, "Família B")
    ingest_external_menu_item(
        db_session,
        family=first_family,
        data=_observation(),
    )
    db_session.flush()

    second_items = list_meal_delivery_menu_items(
        db_session,
        family=second_family,
        provider_key="uber_eats",
        at=NOW + timedelta(minutes=1),
    )

    assert second_items == []


def test_delivery_catalog_hides_expired_offers(db_session: Session) -> None:
    family = _family(db_session, "Família A")
    ingest_external_menu_item(
        db_session,
        family=family,
        data=_observation(),
    )
    db_session.flush()

    items = list_meal_delivery_menu_items(
        db_session,
        family=family,
        provider_key="uber_eats",
        at=NOW + timedelta(hours=7),
    )

    assert items == []
