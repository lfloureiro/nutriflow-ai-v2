from datetime import UTC, datetime
from decimal import Decimal

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.routes.meal_discovery import sync_meal_delivery_provider_endpoint
from app.core.config import settings
from app.models.family import Family
from app.models.meal_candidate_availability import MealCommercialOffer
from app.providers.meal_delivery import MealDeliveryDiscoveryRequest
from app.providers.registry import (
    clear_meal_delivery_adapters,
    register_meal_delivery_adapter,
)
from app.schemas.external_menu import ExternalMenuItemObservationWrite
from app.schemas.meal_delivery_sync import MealDeliverySyncRequest

NOW = datetime(2026, 8, 23, 20, 0, tzinfo=UTC)


class FakeUberAdapter:
    provider_key = "uber_eats"

    def discover_menu_items(
        self,
        request: MealDeliveryDiscoveryRequest,
    ) -> tuple[ExternalMenuItemObservationWrite, ...]:
        return (
            ExternalMenuItemObservationWrite(
                provider_key="uber_eats",
                provider_name="Uber Eats",
                merchant_key="merchant-live-1",
                merchant_name="Restaurante Live",
                item_key="item-live-1",
                item_name="Prato Live",
                source_kind="delivery",
                location=request.delivery_address,
                item_price=Decimal("11.90"),
                currency="EUR",
                observed_at=NOW,
                source_reference="provider://uber_eats/merchant-live-1/item-live-1",
            ),
        )


def _family(db_session: Session) -> Family:
    family = Family(
        name="Família Provider API",
        timezone="Europe/Lisbon",
        meal_discovery_sources=["shared_recipes", "uber_eats"],
        delivery_address="Rua API, Lisboa",
    )
    db_session.add(family)
    db_session.commit()
    db_session.refresh(family)
    return family


def _configure_uber(monkeypatch) -> None:
    monkeypatch.setenv("NUTRIFLOW_UBER_CLIENT_ID", "test-client")
    monkeypatch.setenv("NUTRIFLOW_UBER_CLIENT_SECRET", "test-secret")
    monkeypatch.setattr(settings, "uber_consumer_delivery_enabled", True)


def test_sync_endpoint_rejects_configured_provider_without_adapter(
    db_session: Session,
    monkeypatch,
) -> None:
    clear_meal_delivery_adapters()
    _configure_uber(monkeypatch)
    family = _family(db_session)

    with pytest.raises(HTTPException) as error:
        sync_meal_delivery_provider_endpoint(
            family_id=family.id,
            provider_key="uber_eats",
            payload=MealDeliverySyncRequest(),
            db=db_session,
        )

    assert error.value.status_code == 503
    assert "No executable adapter" in str(error.value.detail)


def test_sync_endpoint_uses_registered_adapter_and_ingests_offer(
    db_session: Session,
    monkeypatch,
) -> None:
    clear_meal_delivery_adapters()
    _configure_uber(monkeypatch)
    family = _family(db_session)

    try:
        register_meal_delivery_adapter(FakeUberAdapter())
        result = sync_meal_delivery_provider_endpoint(
            family_id=family.id,
            provider_key="uber_eats",
            payload=MealDeliverySyncRequest(),
            db=db_session,
        )

        assert result.provider_key == "uber_eats"
        assert result.observed_count == 1
        assert len(result.ingested) == 1
        assert not result.ingested[0].eligible_for_nutrition_ranking
        assert len(result.items) == 1
        assert result.items[0].merchant_name == "Restaurante Live"
        assert result.items[0].item_name == "Prato Live"
        assert result.items[0].item_price == Decimal("11.90")
        assert result.items[0].energy_kcal is None
        assert not result.items[0].eligible_for_nutrition_ranking
        assert db_session.scalar(select(func.count()).select_from(MealCommercialOffer)) == 1
    finally:
        clear_meal_delivery_adapters()
