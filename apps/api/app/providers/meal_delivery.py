from dataclasses import dataclass
from typing import Protocol

from app.schemas.external_menu import ExternalMenuItemObservationWrite


@dataclass(frozen=True)
class MealDeliveryDiscoveryRequest:
    delivery_address: str
    query: str | None = None
    limit: int = 30


class MealDeliveryDiscoveryAdapter(Protocol):
    provider_key: str

    def discover_menu_items(
        self,
        request: MealDeliveryDiscoveryRequest,
    ) -> tuple[ExternalMenuItemObservationWrite, ...]: ...
