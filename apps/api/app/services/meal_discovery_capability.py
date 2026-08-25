from app.core.config import settings
from app.models.family import Family
from app.schemas.meal_discovery_capability import (
    MealDiscoveryCapabilitiesRead,
    MealDiscoveryCapabilityRead,
)
from app.services.meal_delivery_provider import list_meal_delivery_provider_integrations
from app.services.restaurant_discovery import google_restaurant_discovery_configured


def _provider_capability(
    provider_key: str,
    *,
    selected: set[str],
) -> MealDiscoveryCapabilityRead:
    integration = next(
        item
        for item in list_meal_delivery_provider_integrations()
        if item.key == provider_key
    )
    if integration.live:
        status = "ready"
        detail = f"{integration.display_name} live provider adapter is configured."
    elif not integration.credentials_present:
        status = "integration_required"
        detail = (
            f"{integration.display_name} credentials are not configured. {integration.detail}"
        )
    elif not integration.consumer_discovery_enabled:
        status = "integration_required"
        detail = (
            f"Credentials for {integration.display_name} are present, but consumer discovery "
            f"is not enabled/approved. {integration.detail}"
        )
    else:
        status = "integration_required"
        detail = (
            f"{integration.display_name} credentials and consumer access are configured, but no "
            "executable provider adapter is registered in this installation."
        )
    return MealDiscoveryCapabilityRead(
        source=provider_key,
        selected=provider_key in selected,
        supported=integration.live,
        live=integration.live,
        status=status,
        detail=detail,
        credentials_configured=integration.credentials_present,
        access_enabled=integration.consumer_discovery_enabled,
        adapter_available=integration.adapter_available,
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
    google_configured = google_restaurant_discovery_configured()
    google_access_enabled = (
        settings.restaurant_apify_google_enabled
        or settings.restaurant_google_places_enabled
    )
    if not settings.restaurant_discovery_enabled:
        restaurant_status = "disabled"
        restaurant_detail = "Live restaurant discovery is disabled in this installation."
        restaurant_live = False
    elif restaurants_selected and not (family.restaurant_area or "").strip():
        restaurant_status = "needs_configuration"
        restaurant_detail = "Configure a restaurant area before live discovery."
        restaurant_live = False
    elif google_configured:
        restaurant_status = "ready"
        restaurant_detail = (
            "Google restaurant discovery is available through Apify Google Maps or direct "
            "Google Places, with OpenStreetMap reserved as fallback."
        )
        restaurant_live = True
    else:
        restaurant_status = "ready"
        restaurant_detail = (
            "OpenStreetMap fallback discovery is available. Configure an Apify Google Maps "
            "token or Google Places API key to enable quality-ranked Google results."
        )
        restaurant_live = True
    restaurants = MealDiscoveryCapabilityRead(
        source="restaurants",
        selected=restaurants_selected,
        supported=settings.restaurant_discovery_enabled,
        live=restaurant_live,
        status=restaurant_status,
        detail=restaurant_detail,
        credentials_configured=google_configured,
        access_enabled=google_access_enabled,
        adapter_available=True,
    )

    providers = [
        _provider_capability(provider_key, selected=selected)
        for provider_key in ("uber_eats", "glovo", "bolt_food")
    ]
    return MealDiscoveryCapabilitiesRead(
        capabilities=[shared, *providers, restaurants]
    )
