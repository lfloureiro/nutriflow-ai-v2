from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.family import Family
from app.providers.meal_delivery import MealDeliveryDiscoveryRequest
from app.schemas.external_menu import ExternalMenuItemObservationWrite
from app.services.meal_delivery_sync import (
    MealDeliveryProviderUnavailable,
    sync_meal_delivery_provider,
)

NOW = datetime(2026, 8, 23, 19, 30, tzinfo=UTC)


class FakeUberAdapter:
    provider_key = "uber_eats"

    def discover_menu_items(
        self,
        request: MealDeliveryDiscoveryRequest,
    ) -> tuple[ExternalMenuItemObservationWrite, ...]:
        assert request.delivery_address == "Rua Teste, Lisboa"
        return (
            ExternalMenuItemObservationWrite(
                provider_key="uber_eats",
                provider_name="Uber Eats",
                merchant_key="merchant-1",
                merchant_name="Restaurante Teste",
                item_key="item-1",
                item_name="Prato Teste",
                source_kind="delivery",
                location=request.delivery_address,
                item_price=Decimal("9.90"),
                currency="EUR",
                observed_at=NOW,
                source_reference="provider://uber_eats/merchant-1/item-1",
            ),
        )


def _family(db_session: Session) -> Family:
    family = Family(
        name="Família Sync",
        timezone="Europe/Lisbon",
        meal_discovery_sources=["shared_recipes", "uber_eats"],
        delivery_address="Rua Teste, Lisboa",
    )
    db_session.add(family)
    db_session.flush()
    return family


def test_sync_refuses_provider_that_is_not_live(db_session: Session, monkeypatch) -> None:
    monkeypatch.delenv("NUTRIFLOW_UBER_CLIENT_ID", raising=False)
    monkeypatch.delenv("NUTRIFLOW_UBER_CLIENT_SECRET", raising=False)
    monkeypatch.setattr(settings, "uber_consumer_delivery_enabled", False)

    with pytest.raises(MealDeliveryProviderUnavailable):
        sync_meal_delivery_provider(
            db_session,
            family=_family(db_session),
            provider_key="uber_eats",
            adapter=FakeUberAdapter(),
            delivery_address="Rua Teste, Lisboa",
        )


def test_sync_normalizes_provider_observations_into_domain(db_session: Session, monkeypatch) -> None:
    monkeypatch.setenv("NUTRIFLOW_UBER_CLIENT_ID", "test-client")
    monkeypatch.setenv("NUTRIFLOW_UBER_CLIENT_SECRET", "test-secret")
    monkeypatch.setattr(settings, "uber_consumer_delivery_enabled", True)

    result = sync_meal_delivery_provider(
        db_session,
        family=_family(db_session),
        provider_key="uber_eats",
        adapter=FakeUberAdapter(),
        delivery_address=" Rua Teste, Lisboa ",
    )

    assert result.provider_key == "uber_eats"
    assert result.observed_count == 1
    assert len(result.ingested) == 1
    assert not result.ingested[0].eligible_for_nutrition_ranking
