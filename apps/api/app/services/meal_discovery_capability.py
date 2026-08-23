from app.core.config import settings
from app.models.family import Family
from app.schemas.meal_discovery_capability import (
    MealDiscoveryCapabilitiesRead,
    MealDiscoveryCapabilityRead,
)


def build_meal_discovery_capabilities(family: Family) -> MealDiscoveryCapabilitiesRead:
    selected = set(family.meal_discovery_sources)
    shared = MealDiscoveryCapabilityRead(
        source="shared_recipes",
        selected="shared_recipes" in selected,
        supported=True,
        live=False,
        status="ready",
        detail="Shared NutriFlow catalogue and Family recipes are available.",
    )

    restaurants_selected = "restaurants" in selected
    if not settings.restaurant_discovery_enabled:
        restaurant_status = "disabled"
        restaurant_detail = "Live restaurant discovery is disabled in this installation."
        restaurant_live = False
    elif restaurants_selected and not (family.restaurant_area or "").strip():
        restaurant_status = "needs_configuration"
        restaurant_detail = "Configure a restaurant area before live discovery."
        restaurant_live = False
    else:
        restaurant_status = "ready"
        restaurant_detail = "Live OpenStreetMap restaurant discovery is available."
        restaurant_live = True
    restaurants = MealDiscoveryCapabilityRead(
        source="restaurants",
        selected=restaurants_selected,
        supported=settings.restaurant_discovery_enabled,
        live=restaurant_live,
        status=restaurant_status,
        detail=restaurant_detail,
    )

    uber = MealDiscoveryCapabilityRead(
        source="uber_eats",
        selected="uber_eats" in selected,
        supported=False,
        live=False,
        status="integration_required",
        detail="An authorized Uber Eats provider adapter is required for live menus and offers.",
    )
    glovo = MealDiscoveryCapabilityRead(
        source="glovo",
        selected="glovo" in selected,
        supported=False,
        live=False,
        status="integration_required",
        detail="An authorized Glovo provider adapter is required for live menus and offers.",
    )
    return MealDiscoveryCapabilitiesRead(
        capabilities=[shared, uber, glovo, restaurants]
    )
