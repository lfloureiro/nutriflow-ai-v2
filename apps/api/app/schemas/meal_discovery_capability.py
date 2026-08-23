from typing import Literal

from pydantic import BaseModel

from app.schemas.family import MealDiscoverySource

MealDiscoveryCapabilityStatus = Literal[
    "ready",
    "needs_configuration",
    "integration_required",
    "disabled",
]


class MealDiscoveryCapabilityRead(BaseModel):
    source: MealDiscoverySource
    selected: bool
    supported: bool
    live: bool
    status: MealDiscoveryCapabilityStatus
    detail: str
    credentials_configured: bool | None = None
    access_enabled: bool | None = None
    adapter_available: bool | None = None


class MealDiscoveryCapabilitiesRead(BaseModel):
    capabilities: list[MealDiscoveryCapabilityRead]
