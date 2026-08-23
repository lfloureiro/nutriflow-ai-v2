from app.core.config import settings
from app.services.meal_delivery_provider import (
    get_meal_delivery_provider_integration,
    list_meal_delivery_provider_integrations,
)


def test_delivery_provider_registry_is_safe_without_secrets(monkeypatch) -> None:
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
    assert all(not provider.live for provider in providers)


def test_uber_needs_both_secrets_and_explicit_enable(monkeypatch) -> None:
    monkeypatch.setenv("NUTRIFLOW_UBER_CLIENT_ID", "test-client")
    monkeypatch.setenv("NUTRIFLOW_UBER_CLIENT_SECRET", "test-secret")
    monkeypatch.setattr(settings, "uber_consumer_delivery_enabled", False)

    configured = get_meal_delivery_provider_integration("uber_eats")
    assert configured.credentials_present
    assert not configured.live

    monkeypatch.setattr(settings, "uber_consumer_delivery_enabled", True)
    enabled = get_meal_delivery_provider_integration("uber_eats")
    assert enabled.credentials_present
    assert enabled.live
    assert enabled.consumer_discovery_publicly_supported


def test_bolt_credentials_do_not_claim_public_consumer_discovery(monkeypatch) -> None:
    monkeypatch.setenv("NUTRIFLOW_BOLT_FOOD_INTEGRATOR_ID", "test-integrator")
    monkeypatch.setenv("NUTRIFLOW_BOLT_FOOD_SECRET_KEY", "test-secret")
    monkeypatch.setattr(settings, "bolt_food_consumer_discovery_enabled", False)

    bolt = get_meal_delivery_provider_integration("bolt_food")

    assert bolt.credentials_present
    assert not bolt.live
    assert not bolt.consumer_discovery_publicly_supported
