import uuid

from sqlalchemy.orm import Session

from app.models.family import Family
from app.schemas.family import FamilyCreate, FamilyUpdate

DELIVERY_DISCOVERY_SOURCES = frozenset({"uber_eats", "glovo", "bolt_food"})


class FamilyDiscoveryConfigurationError(ValueError):
    pass


def _validate_discovery_configuration(
    *,
    sources: list[str],
    delivery_address: str | None,
    restaurant_area: str | None,
) -> None:
    if not sources:
        raise FamilyDiscoveryConfigurationError("At least one meal discovery source is required.")
    wants_delivery = bool(DELIVERY_DISCOVERY_SOURCES.intersection(sources))
    if wants_delivery and not (delivery_address or "").strip():
        raise FamilyDiscoveryConfigurationError(
            "A delivery address is required when a delivery provider is enabled."
        )
    if "restaurants" in sources and not (restaurant_area or "").strip():
        raise FamilyDiscoveryConfigurationError(
            "A restaurant area is required when restaurant discovery is enabled."
        )


def create_family(db: Session, data: FamilyCreate) -> Family:
    _validate_discovery_configuration(
        sources=list(data.meal_discovery_sources),
        delivery_address=data.delivery_address,
        restaurant_area=data.restaurant_area,
    )
    family = Family(**data.model_dump())
    db.add(family)
    db.commit()
    db.refresh(family)
    return family


def get_family(db: Session, family_id: uuid.UUID) -> Family | None:
    return db.get(Family, family_id)


def update_family(db: Session, family: Family, data: FamilyUpdate) -> Family:
    patch = data.model_dump(exclude_unset=True)
    sources = patch.get("meal_discovery_sources", family.meal_discovery_sources)
    delivery_address = patch.get("delivery_address", family.delivery_address)
    restaurant_area = patch.get("restaurant_area", family.restaurant_area)
    _validate_discovery_configuration(
        sources=list(sources),
        delivery_address=delivery_address,
        restaurant_area=restaurant_area,
    )
    for field, value in patch.items():
        setattr(family, field, value)
    db.commit()
    db.refresh(family)
    return family
