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


class MealDiscoveryCapabilitiesRead(BaseModel):
    capabilities: list[MealDiscoveryCapabilityRead]
