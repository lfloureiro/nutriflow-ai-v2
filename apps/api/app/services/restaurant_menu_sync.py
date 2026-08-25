import hashlib
import re
import unicodedata
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from difflib import SequenceMatcher

from sqlalchemy.orm import Session

from app.models.family import Family
from app.providers.meal_delivery import MealDeliveryDiscoveryRequest
from app.providers.registry import get_registered_meal_delivery_adapter
from app.schemas.external_menu import ExternalMenuItemObservationWrite, ExternalMenuNutritionWrite
from app.schemas.restaurant_discovery import RestaurantDiscoveryPlaceRead
from app.schemas.restaurant_menu_sync import (
    RestaurantMenuItemRead,
    RestaurantMenuRead,
    RestaurantMenuSyncCreate,
    RestaurantMenuSyncRead,
)
from app.services.external_menu_ingestion import ingest_external_menu_item
from app.services.meal_delivery_provider import get_meal_delivery_provider_integration
from app.services.restaurant_discovery import (
    discover_restaurants,
    google_restaurant_discovery_configured,
)
from app.services.restaurant_dish_nutrition import estimate_restaurant_dish_nutrition
from app.services.restaurant_menu_scraper import (
    RestaurantMenuScraperError,
    ScrapedMenuItem,
    scrape_restaurant_menu,
)

RESTAURANT_WEBSITE_PROVIDER_KEY = "restaurant_website"
MENU_VALIDITY = timedelta(days=15)
_GOOGLE_PROVIDERS = frozenset({"google_maps_apify", "google_places"})
_DELIVERY_FALLBACK_PROVIDERS = ("uber_eats", "glovo")


class RestaurantMenuSyncError(ValueError):
    pass


def _area(family: Family, requested: str | None) -> str:
    value = requested or family.restaurant_area
    normalized = " ".join((value or "").split())
    if not normalized:
        raise RestaurantMenuSyncError(
            "Restaurant menu discovery requires a Family restaurant area or an explicit area."
        )
    return normalized


def _item_key(place_id: str, item: ScrapedMenuItem) -> str:
    payload = f"{place_id}\x1f{item.source_url}\x1f{item.name.casefold()}".encode()
    return hashlib.sha256(payload).hexdigest()[:48]


def _official_nutrition(item: ScrapedMenuItem) -> ExternalMenuNutritionWrite | None:
    if item.energy_kcal is None:
        return None
    return ExternalMenuNutritionWrite(
        evidence_level="official",
        basis_reference=item.source_url,
        reference_quantity=Decimal(1),
        reference_unit="serving",
        energy_kcal=item.energy_kcal,
        nutrients=[],
    )


def _normalize_name(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.casefold())
    ascii_text = "".join(
        character
        for character in normalized
        if not unicodedata.combining(character)
    )
    words = re.findall(r"[a-z0-9]+", ascii_text)
    ignored = {"restaurante", "restaurant", "cc", "c", "centro", "comercial"}
    return " ".join(word for word in words if word not in ignored)


def _merchant_matches(restaurant_name: str, merchant_name: str) -> bool:
    expected = _normalize_name(restaurant_name)
    actual = _normalize_name(merchant_name)
    if not expected or not actual:
        return False
    if expected in actual or actual in expected:
        return True
    return SequenceMatcher(None, expected, actual).ratio() >= 0.72


def _estimate_menu_nutrition(
    db: Session,
    *,
    family: Family,
    item: ScrapedMenuItem,
) -> ExternalMenuNutritionWrite | None:
    nutrition = _official_nutrition(item)
    if nutrition is not None:
        return nutrition
    estimate = estimate_restaurant_dish_nutrition(
        db,
        family_id=family.id,
        item=item,
    )
    return None if estimate is None else estimate.nutrition


def _ingest_website_item(
    db: Session,
    *,
    family: Family,
    restaurant: RestaurantDiscoveryPlaceRead,
    area: str,
    observed_at: datetime,
    item: ScrapedMenuItem,
) -> RestaurantMenuItemRead:
    nutrition = _estimate_menu_nutrition(db, family=family, item=item)
    catalog_key: str | None = None
    eligible = False
    if item.price is not None:
        ingested = ingest_external_menu_item(
            db,
            family=family,
            data=ExternalMenuItemObservationWrite(
                provider_key=RESTAURANT_WEBSITE_PROVIDER_KEY,
                provider_name=restaurant.name,
                merchant_key=restaurant.provider_place_id,
                merchant_name=restaurant.name,
                item_key=_item_key(restaurant.provider_place_id, item),
                item_name=item.name,
                description=item.description,
                source_kind="restaurant",
                location=area,
                item_price=item.price,
                currency=item.currency,
                delivery_fee=None,
                minimum_order=None,
                observed_at=observed_at,
                valid_until=observed_at + MENU_VALIDITY,
                source_reference=item.source_url,
                nutrition=nutrition,
            ),
        )
        catalog_key = ingested.catalog_key
        eligible = ingested.eligible_for_nutrition_ranking

    return RestaurantMenuItemRead(
        restaurant_place_id=restaurant.provider_place_id,
        restaurant_name=restaurant.name,
        item_name=item.name,
        description=item.description,
        item_price=item.price,
        currency=item.currency,
        energy_kcal=None if nutrition is None else nutrition.energy_kcal,
        nutrition_evidence_level=(None if nutrition is None else nutrition.evidence_level),
        nutrition_confidence=None if nutrition is None else nutrition.confidence,
        nutrition_basis_reference=(None if nutrition is None else nutrition.basis_reference),
        source_reference=item.source_url,
        catalog_key=catalog_key,
        eligible_for_nutrition_ranking=eligible,
    )


def _delivery_fallback(
    db: Session,
    *,
    family: Family,
    restaurant: RestaurantDiscoveryPlaceRead,
    area: str,
    item_limit: int,
) -> tuple[list[RestaurantMenuItemRead], str | None]:
    delivery_address = (family.delivery_address or area).strip()
    if not delivery_address:
        return [], None

    for provider_key in _DELIVERY_FALLBACK_PROVIDERS:
        if provider_key not in family.meal_discovery_sources:
            continue
        adapter = get_registered_meal_delivery_adapter(provider_key)
        if adapter is None:
            continue
        integration = get_meal_delivery_provider_integration(
            provider_key,
            adapter_available=True,
        )
        if not integration.live:
            continue
        try:
            observations = adapter.discover_menu_items(
                MealDeliveryDiscoveryRequest(
                    delivery_address=delivery_address,
                    query=restaurant.name,
                    limit=item_limit,
                )
            )
        except (RuntimeError, ValueError):
            continue

        matched = [
            observation
            for observation in observations
            if _merchant_matches(restaurant.name, observation.merchant_name)
        ]
        if not matched:
            continue

        menu_items: list[RestaurantMenuItemRead] = []
        for observation in matched[:item_limit]:
            nutrition = observation.nutrition
            if nutrition is None:
                scraped_item = ScrapedMenuItem(
                    name=observation.item_name,
                    description=observation.description,
                    price=observation.item_price,
                    currency=observation.currency,
                    energy_kcal=None,
                    source_url=observation.source_reference,
                )
                nutrition = _estimate_menu_nutrition(
                    db,
                    family=family,
                    item=scraped_item,
                )
            enriched = observation.model_copy(update={"nutrition": nutrition})
            ingested = ingest_external_menu_item(db, family=family, data=enriched)
            menu_items.append(
                RestaurantMenuItemRead(
                    restaurant_place_id=restaurant.provider_place_id,
                    restaurant_name=restaurant.name,
                    item_name=enriched.item_name,
                    description=enriched.description,
                    item_price=enriched.item_price,
                    currency=enriched.currency,
                    energy_kcal=None if nutrition is None else nutrition.energy_kcal,
                    nutrition_evidence_level=(
                        None if nutrition is None else nutrition.evidence_level
                    ),
                    nutrition_confidence=(
                        None if nutrition is None else nutrition.confidence
                    ),
                    nutrition_basis_reference=(
                        None if nutrition is None else nutrition.basis_reference
                    ),
                    source_reference=enriched.source_reference,
                    catalog_key=ingested.catalog_key,
                    eligible_for_nutrition_ranking=ingested.eligible_for_nutrition_ranking,
                )
            )
        return menu_items, provider_key
    return [], None


def sync_restaurant_menus(
    db: Session,
    *,
    family: Family,
    data: RestaurantMenuSyncCreate,
) -> RestaurantMenuSyncRead:
    area = _area(family, data.area)
    discovery = discover_restaurants(area, limit=data.restaurant_limit)
    if (
        google_restaurant_discovery_configured()
        and discovery.provider not in _GOOGLE_PROVIDERS
    ):
        raise RestaurantMenuSyncError(
            "Google restaurant discovery is configured but unavailable. Restaurant menu sync "
            "will not mix OpenStreetMap fallback results into recommendations."
        )

    observed_at = datetime.now(UTC)
    menus: list[RestaurantMenuRead] = []
    ingested_count = 0
    nutrition_ready_count = 0

    for restaurant in discovery.restaurants:
        menu_source = restaurant.menu_url or restaurant.website
        scraped_error: str | None = None
        pages_scanned: list[str] = []
        menu_items: list[RestaurantMenuItemRead] = []

        if menu_source:
            try:
                scraped = scrape_restaurant_menu(
                    menu_source,
                    max_items=data.item_limit_per_restaurant,
                )
                pages_scanned = list(scraped.pages_scanned)
                menu_items = [
                    _ingest_website_item(
                        db,
                        family=family,
                        restaurant=restaurant,
                        area=area,
                        observed_at=observed_at,
                        item=item,
                    )
                    for item in scraped.items
                ]
            except RestaurantMenuScraperError as exc:
                scraped_error = str(exc)
        else:
            scraped_error = (
                "O restaurante não publica um website ou URL de ementa utilizável no Google."
            )

        if not menu_items:
            fallback_items, provider_key = _delivery_fallback(
                db,
                family=family,
                restaurant=restaurant,
                area=area,
                item_limit=data.item_limit_per_restaurant,
            )
            if fallback_items:
                menu_items = fallback_items
                pages_scanned = list(
                    dict.fromkeys(item.source_reference for item in fallback_items)
                )
                scraped_error = None
                if provider_key:
                    pages_scanned.insert(0, f"delivery:{provider_key}")

        ingested_count += sum(item.catalog_key is not None for item in menu_items)
        nutrition_ready_count += sum(
            item.eligible_for_nutrition_ranking for item in menu_items
        )
        menus.append(
            RestaurantMenuRead(
                restaurant=restaurant,
                pages_scanned=pages_scanned,
                items=menu_items,
                error=(
                    scraped_error
                    if not menu_items
                    else None
                ),
            )
        )

    db.commit()
    return RestaurantMenuSyncRead(
        provider=discovery.provider,
        area=area,
        observed_at=observed_at,
        menus=menus,
        ingested_item_count=ingested_count,
        nutrition_ready_item_count=nutrition_ready_count,
    )
