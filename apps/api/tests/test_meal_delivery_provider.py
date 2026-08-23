from app.core.config import settings
from app.providers.registry import clear_meal_delivery_adapters
from app.services.meal_delivery_provider import (
    get_meal_delivery_provider_integration,
    list_meal_delivery_provider_integrations,
)


def test_delivery_provider_registry_is_safe_without_secrets(monkeypatch) -> None:
    clear_meal_delivery_adapters()
    for name in (
        "NUTRIFLOW_UBER_CLIENT_ID",
        "NUTRIFLOW_UBER_CLIENT_SECRET",
        "NUTRIFLOW_GLOVO_CLIENT_ID",
        "NUTRIFLOW_GLOVO_CLIENT_SECRET",
        "NUTRIFLOW_BOLT_FOOD_INTEGRATOR_ID",
        "NUTRIFLOW_BOLT_FOOD_SECRET_KEY",
    ):
        monkeypatch.delenv(name, raising=False)

    providers = list_meal_delivery_provider_integrations()

    assert [provider.key for provider in providers] == [
        "uber_eats",
        "glovo",
        "bolt_food",
    ]
    assert all(not provider.credentials_present for provider in providers)
    assert all(not provider.adapter_available for provider in providers)
    assert all(not provider.live for provider in providers)


def test_uber_needs_secrets_enable_and_executable_adapter(monkeypatch) -> None:
    clear_meal_delivery_adapters()
    monkeypatch.setenv("NUTRIFLOW_UBER_CLIENT_ID", "test-client")
    monkeypatch.setenv("NUTRIFLOW_UBER_CLIENT_SECRET", "test-secret")
    monkeypatch.setattr(settings, "uber_consumer_delivery_enabled", False)

    disabled = get_meal_delivery_provider_integration(
        "uber_eats",
        adapter_available=True,
    )
    assert disabled.credentials_present
    assert disabled.adapter_available
    assert not disabled.configured
    assert not disabled.live

    monkeypatch.setattr(settings, "uber_consumer_delivery_enabled", True)
    without_adapter = get_meal_delivery_provider_integration("uber_eats")
    assert without_adapter.credentials_present
    assert without_adapter.configured
    assert not without_adapter.adapter_available
    assert not without_adapter.live

    ready = get_meal_delivery_provider_integration(
        "uber_eats",
        adapter_available=True,
    )
    assert ready.configured
    assert ready.adapter_available
    assert ready.live
    assert ready.consumer_discovery_publicly_supported


def test_bolt_credentials_do_not_claim_public_consumer_discovery(monkeypatch) -> None:
    clear_meal_delivery_adapters()
    monkeypatch.setenv("NUTRIFLOW_BOLT_FOOD_INTEGRATOR_ID", "test-integrator")
    monkeypatch.setenv("NUTRIFLOW_BOLT_FOOD_SECRET_KEY", "test-secret")
    monkeypatch.setattr(settings, "bolt_food_consumer_discovery_enabled", False)

    bolt = get_meal_delivery_provider_integration("bolt_food")

    assert bolt.credentials_present
    assert not bolt.configured
    assert not bolt.live
    assert not bolt.consumer_discovery_publicly_supported
