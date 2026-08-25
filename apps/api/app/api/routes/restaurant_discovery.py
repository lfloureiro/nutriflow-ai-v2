import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.restaurant_discovery import RestaurantDiscoveryRead
from app.schemas.restaurant_menu_sync import RestaurantMenuSyncCreate, RestaurantMenuSyncRead
from app.services.family import get_family
from app.services.restaurant_discovery import RestaurantDiscoveryError, discover_restaurants
from app.services.restaurant_menu_sync import RestaurantMenuSyncError, sync_restaurant_menus

router = APIRouter(prefix="/families", tags=["restaurant-discovery"])


@router.get(
    "/{family_id}/restaurant-discovery",
    response_model=RestaurantDiscoveryRead,
)
def discover_family_restaurants_endpoint(
    family_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    area: Annotated[str | None, Query(max_length=255)] = None,
    limit: Annotated[int, Query(ge=1, le=40)] = 20,
) -> RestaurantDiscoveryRead:
    family = get_family(db, family_id)
    if family is None:
        raise HTTPException(status_code=404, detail="Family not found")

    requested_area = (area or family.restaurant_area or "").strip()
    if not requested_area:
        raise HTTPException(
            status_code=422,
            detail="Configure a restaurant area or provide one for this search.",
        )

    try:
        return discover_restaurants(requested_area, limit=limit)
    except RestaurantDiscoveryError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post(
    "/{family_id}/restaurant-menus/sync",
    response_model=RestaurantMenuSyncRead,
)
def sync_family_restaurant_menus_endpoint(
    family_id: uuid.UUID,
    data: RestaurantMenuSyncCreate,
    db: Annotated[Session, Depends(get_db)],
) -> RestaurantMenuSyncRead:
    family = get_family(db, family_id)
    if family is None:
        raise HTTPException(status_code=404, detail="Family not found")
    if "restaurants" not in family.meal_discovery_sources:
        raise HTTPException(
            status_code=409,
            detail="Restaurant discovery is not enabled for this Family.",
        )

    try:
        return sync_restaurant_menus(db, family=family, data=data)
    except RestaurantDiscoveryError as exc:
        db.rollback()
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except RestaurantMenuSyncError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
