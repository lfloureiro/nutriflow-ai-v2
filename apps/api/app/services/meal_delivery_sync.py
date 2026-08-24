from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.family import Family
from app.providers.meal_delivery import (
    MealDeliveryDiscoveryAdapter,
    MealDeliveryDiscoveryRequest,
)
from app.providers.registry import get_registered_meal_delivery_adapter
from app.schemas.external_menu import (
    ExternalMenuItemIngestedRead,
    ExternalMenuItemObservationWrite,
)
from app.services.external_menu_ingestion import ingest_external_menu_item
from app.services.meal_delivery_provider import get_meal_delivery_provider_integration


class MealDeliveryProviderUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class MealDeliverySyncResult:
    provider_key: str
    observed_count: int
    observations: tuple[ExternalMenuItemObservationWrite, ...]
    ingested: tuple[ExternalMenuItemIngestedRead, ...]


def sync_meal_delivery_provider(
    db: Session,
    *,
    family: Family,
    provider_key: str,
    adapter: MealDeliveryDiscoveryAdapter,
    delivery_address: str,
    query: str | None = None,
    limit: int = 30,
) -> MealDeliverySyncResult:
    integration = get_meal_delivery_provider_integration(
        provider_key,
        adapter_available=True,
    )
    if not integration.live:
        raise MealDeliveryProviderUnavailable(
            f"{integration.display_name} consumer discovery is not enabled for this installation."
        )
    if adapter.provider_key != provider_key:
        raise ValueError(
            f"Adapter provider mismatch: expected {provider_key}, got {adapter.provider_key}."
        )
    address = delivery_address.strip()
    if not address:
        raise ValueError("delivery_address is required for provider discovery.")
    if limit < 1 or limit > 100:
        raise ValueError("limit must be between 1 and 100.")

    observations = adapter.discover_menu_items(
        MealDeliveryDiscoveryRequest(
            delivery_address=address,
            query=query,
            limit=limit,
        )
    )
    if len(observations) > limit:
        observations = observations[:limit]

    ingested: list[ExternalMenuItemIngestedRead] = []
    for observation in observations:
        if observation.provider_key != provider_key:
            raise ValueError(
                "Provider adapter returned an observation for a different provider."
            )
        if observation.source_kind != "delivery":
            raise ValueError("Delivery provider adapters must return delivery observations.")
        ingested.append(
            ingest_external_menu_item(
                db,
                family=family,
                data=observation,
            )
        )

    return MealDeliverySyncResult(
        provider_key=provider_key,
        observed_count=len(observations),
        observations=tuple(observations),
        ingested=tuple(ingested),
    )


def sync_registered_meal_delivery_provider(
    db: Session,
    *,
    family: Family,
    provider_key: str,
    delivery_address: str,
    query: str | None = None,
    limit: int = 30,
) -> MealDeliverySyncResult:
    adapter = get_registered_meal_delivery_adapter(provider_key)
    if adapter is None:
        raise MealDeliveryProviderUnavailable(
            f"No executable adapter is registered for provider {provider_key}."
        )
    return sync_meal_delivery_provider(
        db,
        family=family,
        provider_key=provider_key,
        adapter=adapter,
        delivery_address=delivery_address,
        query=query,
        limit=limit,
    )
