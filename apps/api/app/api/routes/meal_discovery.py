import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.meal_delivery_sync import (
    MealDeliveryMenuItemRead,
    MealDeliveryProviderKey,
    MealDeliverySyncRead,
    MealDeliverySyncRequest,
)
from app.schemas.meal_discovery_capability import MealDiscoveryCapabilitiesRead
from app.services.family import get_family
from app.services.meal_delivery_catalog import list_meal_delivery_menu_items
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


@router.get(
    "/{family_id}/meal-discovery/providers/{provider_key}/items",
    response_model=list[MealDeliveryMenuItemRead],
)
def list_meal_delivery_provider_items_endpoint(
    family_id: uuid.UUID,
    provider_key: MealDeliveryProviderKey,
    db: Annotated[Session, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> list[MealDeliveryMenuItemRead]:
    family = get_family(db, family_id)
    if family is None:
        raise HTTPException(status_code=404, detail="Family not found")
    if provider_key not in family.meal_discovery_sources:
        raise HTTPException(
            status_code=409,
            detail="Provider is not enabled in this Family meal discovery configuration.",
        )
    return list_meal_delivery_menu_items(
        db,
        family=family,
        provider_key=provider_key,
        limit=limit,
    )


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
    items = [
        MealDeliveryMenuItemRead(
            catalog_key=ingested.catalog_key,
            merchant_name=observation.merchant_name,
            item_name=observation.item_name,
            description=observation.description,
            item_price=observation.item_price,
            currency=observation.currency,
            delivery_fee=observation.delivery_fee,
            minimum_order=observation.minimum_order,
            source_reference=observation.source_reference,
            observed_at=observation.observed_at,
            energy_kcal=(
                observation.nutrition.energy_kcal
                if observation.nutrition is not None
                else None
            ),
            nutrition_evidence_level=(
                observation.nutrition.evidence_level
                if observation.nutrition is not None
                else None
            ),
            nutrition_confidence=(
                observation.nutrition.confidence
                if observation.nutrition is not None
                else None
            ),
            eligible_for_nutrition_ranking=ingested.eligible_for_nutrition_ranking,
        )
        for observation, ingested in zip(
            result.observations,
            result.ingested,
            strict=True,
        )
    ]
    return MealDeliverySyncRead(
        provider_key=provider_key,
        observed_count=result.observed_count,
        ingested=list(result.ingested),
        items=items,
    )
