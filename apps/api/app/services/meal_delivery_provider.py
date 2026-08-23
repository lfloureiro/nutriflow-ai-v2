from dataclasses import dataclass

from app.core.config import settings
from app.core.provider_secrets import secrets_present


@dataclass(frozen=True)
class MealDeliveryProviderIntegration:
    key: str
    display_name: str
    credentials_present: bool
    consumer_discovery_enabled: bool
    consumer_discovery_publicly_supported: bool
    detail: str

    @property
    def live(self) -> bool:
        return self.credentials_present and self.consumer_discovery_enabled


_PROVIDER_SECRETS = {
    "uber_eats": ("NUTRIFLOW_UBER_CLIENT_ID", "NUTRIFLOW_UBER_CLIENT_SECRET"),
    "glovo": ("NUTRIFLOW_GLOVO_CLIENT_ID", "NUTRIFLOW_GLOVO_CLIENT_SECRET"),
    "bolt_food": ("NUTRIFLOW_BOLT_FOOD_INTEGRATOR_ID", "NUTRIFLOW_BOLT_FOOD_SECRET_KEY"),
}


def get_meal_delivery_provider_integration(
    provider_key: str,
) -> MealDeliveryProviderIntegration:
    if provider_key == "uber_eats":
        return MealDeliveryProviderIntegration(
            key=provider_key,
            display_name="Uber Eats",
            credentials_present=secrets_present(*_PROVIDER_SECRETS[provider_key]),
            consumer_discovery_enabled=settings.uber_consumer_delivery_enabled,
            consumer_discovery_publicly_supported=True,
            detail=(
                "Uber Consumer Delivery access is early-access and must be approved for this app."
            ),
        )
    if provider_key == "glovo":
        return MealDeliveryProviderIntegration(
            key=provider_key,
            display_name="Glovo",
            credentials_present=secrets_present(*_PROVIDER_SECRETS[provider_key]),
            consumer_discovery_enabled=settings.glovo_consumer_discovery_enabled,
            consumer_discovery_publicly_supported=False,
            detail=(
                "The public Glovo APIs currently documented for partners do not expose a general "
                "consumer marketplace discovery contract."
            ),
        )
    if provider_key == "bolt_food":
        return MealDeliveryProviderIntegration(
            key=provider_key,
            display_name="Bolt Food",
            credentials_present=secrets_present(*_PROVIDER_SECRETS[provider_key]),
            consumer_discovery_enabled=settings.bolt_food_consumer_discovery_enabled,
            consumer_discovery_publicly_supported=False,
            detail=(
                "The public Bolt Food API is a merchant/POS integration; consumer marketplace "
                "discovery requires a separate approved contract if Bolt provides one."
            ),
        )
    raise ValueError(f"Unknown meal delivery provider: {provider_key}")


def list_meal_delivery_provider_integrations() -> tuple[MealDeliveryProviderIntegration, ...]:
    return tuple(
        get_meal_delivery_provider_integration(provider_key)
        for provider_key in ("uber_eats", "glovo", "bolt_food")
    )
