from app.core.config import settings
from app.models.family import Family
from app.providers.meal_delivery import MealDeliveryDiscoveryRequest
from app.providers.registry import (
    clear_meal_delivery_adapters,
    register_meal_delivery_adapter,
)
from app.schemas.external_menu import ExternalMenuItemObservationWrite
from app.services.meal_discovery_capability import build_meal_discovery_capabilities


class FakeUberAdapter:
    provider_key = "uber_eats"

    def discover_menu_items(
        self,
        request: MealDeliveryDiscoveryRequest,
    ) -> tuple[ExternalMenuItemObservationWrite, ...]:
        del request
        return ()


def test_capabilities_report_recipes_restaurants_and_delivery_integrations(monkeypatch) -> None:
    clear_meal_delivery_adapters()
    secret_names = (
        "NUTRIFLOW_APIFY_API_TOKEN",
        "NUTRIFLOW_GOOGLE_PLACES_API_KEY",
        "NUTRIFLOW_UBER_CLIENT_ID",
        "NUTRIFLOW_UBER_CLIENT_SECRET",
        "NUTRIFLOW_GLOVO_CLIENT_ID",
        "NUTRIFLOW_GLOVO_CLIENT_SECRET",
        "NUTRIFLOW_BOLT_FOOD_INTEGRATOR_ID",
        "NUTRIFLOW_BOLT_FOOD_SECRET_KEY",
    )
    for name in secret_names:
        monkeypatch.delenv(name, raising=False)
        monkeypatch.setattr(settings, name.casefold(), None)
    monkeypatch.setattr(settings, "restaurant_discovery_enabled", True)
    monkeypatch.setattr(settings, "restaurant_apify_google_enabled", True)
    monkeypatch.setattr(settings, "restaurant_google_places_enabled", True)
    monkeypatch.setattr(settings, "uber_consumer_delivery_enabled", False)
    monkeypatch.setattr(settings, "glovo_consumer_discovery_enabled", False)
    monkeypatch.setattr(settings, "bolt_food_consumer_discovery_enabled", False)

    family = Family(
        name="Família",
        timezone="Europe/Lisbon",
        meal_discovery_sources=[
            "shared_recipes",
            "uber_eats",
            "glovo",
            "bolt_food",
            "restaurants",
        ],
        delivery_address="Rua Exemplo, Lisboa",
        restaurant_area="Benfica, Lisboa",
    )

    result = build_meal_discovery_capabilities(family)
    by_source = {item.source: item for item in result.capabilities}

    assert set(by_source) == {
        "shared_recipes",
        "uber_eats",
        "glovo",
        "bolt_food",
        "restaurants",
    }
    assert by_source["shared_recipes"].status == "ready"
    assert by_source["shared_recipes"].credentials_configured is None
    restaurants = by_source["restaurants"]
    assert restaurants.status == "ready"
    assert restaurants.live
    assert restaurants.credentials_configured is False
    assert "OpenStreetMap fallback" in restaurants.detail
    for source in ("uber_eats", "glovo", "bolt_food"):
        capability = by_source[source]
        assert capability.status == "integration_required"
        assert not capability.live
        assert capability.credentials_configured is False
        assert capability.access_enabled is False
        assert capability.adapter_available is False


def test_restaurant_capability_prefers_google_when_key_is_configured(monkeypatch) -> None:
    monkeypatch.setenv("NUTRIFLOW_GOOGLE_PLACES_API_KEY", "test-google-key")
    monkeypatch.setattr(settings, "restaurant_discovery_enabled", True)
    monkeypatch.setattr(settings, "restaurant_google_places_enabled", True)
    family = Family(
        name="Família Google",
        timezone="Europe/Lisbon",
        meal_discovery_sources=["restaurants"],
        restaurant_area="Benfica, Lisboa",
    )

    result = build_meal_discovery_capabilities(family)
    restaurants = next(
        item for item in result.capabilities if item.source == "restaurants"
    )

    assert restaurants.status == "ready"
    assert restaurants.live
    assert restaurants.credentials_configured is True
    assert "Google Places" in restaurants.detail


def test_uber_capability_requires_credentials_enable_and_registered_adapter(monkeypatch) -> None:
    clear_meal_delivery_adapters()
    monkeypatch.setenv("NUTRIFLOW_UBER_CLIENT_ID", "test-client")
    monkeypatch.setenv("NUTRIFLOW_UBER_CLIENT_SECRET", "test-secret")
    monkeypatch.setattr(settings, "uber_consumer_delivery_enabled", True)

    family = Family(
        name="Família",
        timezone="Europe/Lisbon",
        meal_discovery_sources=["shared_recipes", "uber_eats"],
        delivery_address="Rua Exemplo, Lisboa",
    )

    without_adapter = build_meal_discovery_capabilities(family)
    uber = next(
        item for item in without_adapter.capabilities if item.source == "uber_eats"
    )
    assert uber.status == "integration_required"
    assert not uber.supported
    assert not uber.live
    assert uber.credentials_configured is True
    assert uber.access_enabled is True
    assert uber.adapter_available is False
    assert "no executable provider adapter" in uber.detail

    try:
        register_meal_delivery_adapter(FakeUberAdapter())
        with_adapter = build_meal_discovery_capabilities(family)
        uber = next(
            item for item in with_adapter.capabilities if item.source == "uber_eats"
        )
        assert uber.status == "ready"
        assert uber.supported
        assert uber.live
        assert uber.credentials_configured is True
        assert uber.access_enabled is True
        assert uber.adapter_available is True
    finally:
        clear_meal_delivery_adapters()
