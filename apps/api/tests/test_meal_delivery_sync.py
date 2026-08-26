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


class FakeLiYuanAdapter:
    provider_key = "uber_eats"

    def discover_menu_items(
        self,
        request: MealDeliveryDiscoveryRequest,
    ) -> tuple[ExternalMenuItemObservationWrite, ...]:
        return (
            ExternalMenuItemObservationWrite(
                provider_key="uber_eats",
                provider_name="Uber Eats",
                merchant_key="li-yuan-colombo",
                merchant_name="Restaurante Li Yuan (C. C. Colombo)",
                item_key="beef-oyster-fried-rice",
                item_name="4. Vaca com Molho de Ostras e Arroz Chao Chao",
                source_kind="delivery",
                location=request.delivery_address,
                item_price=Decimal("12.40"),
                currency="EUR",
                observed_at=NOW,
                source_reference=(
                    "https://www.ubereats.com/pt/store/restaurante-li-yuan/example"
                ),
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


def _disable_apify(monkeypatch) -> None:
    monkeypatch.delenv("NUTRIFLOW_APIFY_API_TOKEN", raising=False)
    monkeypatch.setattr(settings, "nutriflow_apify_api_token", None)
    monkeypatch.setattr(settings, "meal_delivery_apify_enabled", False)


def _enable_official_test_provider(monkeypatch) -> None:
    _disable_apify(monkeypatch)
    monkeypatch.setenv("NUTRIFLOW_UBER_CLIENT_ID", "test-client")
    monkeypatch.setenv("NUTRIFLOW_UBER_CLIENT_SECRET", "test-secret")
    monkeypatch.setattr(settings, "uber_consumer_delivery_enabled", True)


def test_sync_refuses_provider_that_is_not_live(db_session: Session, monkeypatch) -> None:
    _disable_apify(monkeypatch)
    monkeypatch.delenv("NUTRIFLOW_UBER_CLIENT_ID", raising=False)
    monkeypatch.delenv("NUTRIFLOW_UBER_CLIENT_SECRET", raising=False)
    monkeypatch.setattr(settings, "nutriflow_uber_client_id", None)
    monkeypatch.setattr(settings, "nutriflow_uber_client_secret", None)
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
    _enable_official_test_provider(monkeypatch)

    result = sync_meal_delivery_provider(
        db_session,
        family=_family(db_session),
        provider_key="uber_eats",
        adapter=FakeUberAdapter(),
        delivery_address=" Rua Teste, Lisboa ",
    )

    assert result.provider_key == "uber_eats"
    assert result.observed_count == 1
    assert len(result.observations) == 1
    assert result.observations[0].item_name == "Prato Teste"
    assert len(result.ingested) == 1
    assert not result.ingested[0].eligible_for_nutrition_ranking


def test_sync_estimates_structural_nutrition_for_delivery_dish(
    db_session: Session,
    monkeypatch,
) -> None:
    _enable_official_test_provider(monkeypatch)

    result = sync_meal_delivery_provider(
        db_session,
        family=_family(db_session),
        provider_key="uber_eats",
        adapter=FakeLiYuanAdapter(),
        delivery_address="Rua Teste, Lisboa",
    )

    observation = result.observations[0]
    assert observation.nutrition is not None
    assert observation.nutrition.evidence_level == "estimated"
    assert Decimal(550) <= observation.nutrition.energy_kcal <= Decimal(850)
    assert observation.nutrition.confidence is not None
    assert observation.nutrition.basis_reference is not None
    assert observation.nutrition.basis_reference.startswith(
        "nutriflow-structural-dish-estimate-v1"
    )
    assert result.ingested[0].eligible_for_nutrition_ranking
    assert result.ingested[0].composition_id is not None
