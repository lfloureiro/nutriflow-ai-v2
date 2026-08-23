from dataclasses import dataclass

from app.core.config import settings
from app.core.provider_secrets import secrets_present
from app.providers.registry import has_registered_meal_delivery_adapter


@dataclass(frozen=True)
class MealDeliveryProviderIntegration:
    key: str
    display_name: str
    credentials_present: bool
    consumer_discovery_enabled: bool
    adapter_available: bool
    consumer_discovery_publicly_supported: bool
    detail: str

    @property
    def configured(self) -> bool:
        return self.credentials_present and self.consumer_discovery_enabled

    @property
    def live(self) -> bool:
        return self.configured and self.adapter_available


_PROVIDER_SECRETS = {
    "uber_eats": ("NUTRIFLOW_UBER_CLIENT_ID", "NUTRIFLOW_UBER_CLIENT_SECRET"),
    "glovo": ("NUTRIFLOW_GLOVO_CLIENT_ID", "NUTRIFLOW_GLOVO_CLIENT_SECRET"),
    "bolt_food": ("NUTRIFLOW_BOLT_FOOD_INTEGRATOR_ID", "NUTRIFLOW_BOLT_FOOD_SECRET_KEY"),
}


def _integration(
    *,
    provider_key: str,
    display_name: str,
    consumer_discovery_enabled: bool,
    consumer_discovery_publicly_supported: bool,
    detail: str,
    adapter_available: bool | None,
) -> MealDeliveryProviderIntegration:
    return MealDeliveryProviderIntegration(
        key=provider_key,
        display_name=display_name,
        credentials_present=secrets_present(*_PROVIDER_SECRETS[provider_key]),
        consumer_discovery_enabled=consumer_discovery_enabled,
        adapter_available=(
            has_registered_meal_delivery_adapter(provider_key)
            if adapter_available is None
            else adapter_available
        ),
        consumer_discovery_publicly_supported=consumer_discovery_publicly_supported,
        detail=detail,
    )


def get_meal_delivery_provider_integration(
    provider_key: str,
    *,
    adapter_available: bool | None = None,
) -> MealDeliveryProviderIntegration:
    if provider_key == "uber_eats":
        return _integration(
            provider_key=provider_key,
            display_name="Uber Eats",
            consumer_discovery_enabled=settings.uber_consumer_delivery_enabled,
            consumer_discovery_publicly_supported=True,
            detail=(
                "Uber Consumer Delivery access is early-access and must be approved for this app."
            ),
            adapter_available=adapter_available,
        )
    if provider_key == "glovo":
        return _integration(
            provider_key=provider_key,
            display_name="Glovo",
            consumer_discovery_enabled=settings.glovo_consumer_discovery_enabled,
            consumer_discovery_publicly_supported=False,
            detail=(
                "The public Glovo APIs currently documented for partners do not expose a general "
                "consumer marketplace discovery contract."
            ),
            adapter_available=adapter_available,
        )
    if provider_key == "bolt_food":
        return _integration(
            provider_key=provider_key,
            display_name="Bolt Food",
            consumer_discovery_enabled=settings.bolt_food_consumer_discovery_enabled,
            consumer_discovery_publicly_supported=False,
            detail=(
                "The public Bolt Food API is a merchant/POS integration; consumer marketplace "
                "discovery requires a separate approved contract if Bolt provides one."
            ),
            adapter_available=adapter_available,
        )
    raise ValueError(f"Unknown meal delivery provider: {provider_key}")


def list_meal_delivery_provider_integrations() -> tuple[MealDeliveryProviderIntegration, ...]:
    return tuple(
        get_meal_delivery_provider_integration(provider_key)
        for provider_key in ("uber_eats", "glovo", "bolt_food")
    )
