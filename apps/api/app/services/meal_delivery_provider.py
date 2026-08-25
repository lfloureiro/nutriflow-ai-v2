from dataclasses import dataclass

from app.core.config import settings
from app.core.provider_secrets import get_provider_secret_store, secrets_present
from app.providers.registry import has_registered_meal_delivery_adapter

APIFY_API_TOKEN_SECRET = "NUTRIFLOW_APIFY_API_TOKEN"


@dataclass(frozen=True)
class MealDeliveryProviderIntegration:
    key: str
    display_name: str
    credentials_present: bool
    consumer_discovery_enabled: bool
    adapter_available: bool
    consumer_discovery_publicly_supported: bool
    detail: str
    public_web_discovery_configured: bool = False

    @property
    def configured(self) -> bool:
        official = self.credentials_present and self.consumer_discovery_enabled
        return official or self.public_web_discovery_configured

    @property
    def live(self) -> bool:
        return self.configured and self.adapter_available


_PROVIDER_SECRETS = {
    "uber_eats": ("NUTRIFLOW_UBER_CLIENT_ID", "NUTRIFLOW_UBER_CLIENT_SECRET"),
    "glovo": ("NUTRIFLOW_GLOVO_CLIENT_ID", "NUTRIFLOW_GLOVO_CLIENT_SECRET"),
    "bolt_food": ("NUTRIFLOW_BOLT_FOOD_INTEGRATOR_ID", "NUTRIFLOW_BOLT_FOOD_SECRET_KEY"),
}


def _public_web_discovery(provider_key: str) -> bool:
    if provider_key not in {"uber_eats", "glovo"}:
        return False
    return (
        settings.meal_delivery_apify_enabled
        and get_provider_secret_store().get(APIFY_API_TOKEN_SECRET) is not None
    )


def _integration(
    *,
    provider_key: str,
    display_name: str,
    consumer_discovery_enabled: bool,
    consumer_discovery_publicly_supported: bool,
    detail: str,
    adapter_available: bool | None,
) -> MealDeliveryProviderIntegration:
    public_web = _public_web_discovery(provider_key)
    if public_web:
        detail = (
            f"{display_name} public marketplace discovery is available through the "
            "configured Apify adapter. Official provider access remains optional."
        )
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
        public_web_discovery_configured=public_web,
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
