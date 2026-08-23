import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.meal_delivery_sync import (
    MealDeliveryProviderKey,
    MealDeliverySyncRead,
    MealDeliverySyncRequest,
)
from app.schemas.meal_discovery_capability import MealDiscoveryCapabilitiesRead
from app.services.family import get_family
from app.services.meal_delivery_sync import (
    MealDeliveryProviderUnavailable,
    sync_registered_meal_delivery_provider,
)
from app.services.meal_discovery_capability import build_meal_discovery_capabilities

router = APIRouter(prefix="/families", tags=["meal-discovery"])


@router.get(
    "/{family_id}/meal-discovery-capabilities",
    response_model=MealDiscoveryCapabilitiesRead,
)
def get_meal_discovery_capabilities_endpoint(
    family_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
) -> MealDiscoveryCapabilitiesRead:
    family = get_family(db, family_id)
    if family is None:
        raise HTTPException(status_code=404, detail="Family not found")
    return build_meal_discovery_capabilities(family)


@router.post(
    "/{family_id}/meal-discovery/providers/{provider_key}/sync",
    response_model=MealDeliverySyncRead,
)
def sync_meal_delivery_provider_endpoint(
    family_id: uuid.UUID,
    provider_key: MealDeliveryProviderKey,
    payload: MealDeliverySyncRequest,
    db: Annotated[Session, Depends(get_db)],
) -> MealDeliverySyncRead:
    family = get_family(db, family_id)
    if family is None:
        raise HTTPException(status_code=404, detail="Family not found")
    if provider_key not in family.meal_discovery_sources:
        raise HTTPException(
            status_code=409,
            detail="Provider is not enabled in this Family meal discovery configuration.",
        )

    delivery_address = (payload.delivery_address or family.delivery_address or "").strip()
    if not delivery_address:
        raise HTTPException(
            status_code=422,
            detail="A delivery address is required for provider discovery.",
        )

    try:
        result = sync_registered_meal_delivery_provider(
            db,
            family=family,
            provider_key=provider_key,
            delivery_address=delivery_address,
            query=payload.query,
            limit=payload.limit,
        )
    except MealDeliveryProviderUnavailable as exc:
        db.rollback()
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    db.commit()
    return MealDeliverySyncRead(
        provider_key=provider_key,
        observed_count=result.observed_count,
        ingested=list(result.ingested),
    )
