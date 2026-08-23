import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.meal_discovery_capability import MealDiscoveryCapabilitiesRead
from app.services.family import get_family
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
