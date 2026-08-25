import hashlib
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.family import Family
from app.schemas.external_menu import ExternalMenuItemObservationWrite, ExternalMenuNutritionWrite
from app.schemas.restaurant_menu_sync import (
    RestaurantMenuItemRead,
    RestaurantMenuRead,
    RestaurantMenuSyncCreate,
    RestaurantMenuSyncRead,
)
from app.services.external_menu_ingestion import ingest_external_menu_item
from app.services.restaurant_discovery import discover_restaurants, google_places_configured
from app.services.restaurant_dish_nutrition import estimate_restaurant_dish_nutrition
from app.services.restaurant_menu_scraper import (
    RestaurantMenuScraperError,
    ScrapedMenuItem,
    scrape_restaurant_menu,
)

RESTAURANT_WEBSITE_PROVIDER_KEY = "restaurant_website"
MENU_VALIDITY = timedelta(days=15)


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


def sync_restaurant_menus(
    db: Session,
    *,
    family: Family,
    data: RestaurantMenuSyncCreate,
) -> RestaurantMenuSyncRead:
    area = _area(family, data.area)
    discovery = discover_restaurants(area, limit=data.restaurant_limit)
    if google_places_configured() and discovery.provider != "google_places":
        raise RestaurantMenuSyncError(
            "Google Places is configured but unavailable. Restaurant menu sync will not mix "
            "OpenStreetMap fallback results into recommendations."
        )

    observed_at = datetime.now(UTC)
    menus: list[RestaurantMenuRead] = []
    ingested_count = 0
    nutrition_ready_count = 0

    for restaurant in discovery.restaurants:
        if not restaurant.website:
            menus.append(
                RestaurantMenuRead(
                    restaurant=restaurant,
                    pages_scanned=[],
                    items=[],
                    error="O restaurante não publica um website oficial utilizável.",
                )
            )
            continue
        try:
            scraped = scrape_restaurant_menu(
                restaurant.website,
                max_items=data.item_limit_per_restaurant,
            )
        except RestaurantMenuScraperError as exc:
            menus.append(
                RestaurantMenuRead(
                    restaurant=restaurant,
                    pages_scanned=[],
                    items=[],
                    error=str(exc),
                )
            )
            continue

        menu_items: list[RestaurantMenuItemRead] = []
        for item in scraped.items:
            nutrition = _official_nutrition(item)
            if nutrition is None:
                estimate = estimate_restaurant_dish_nutrition(
                    db,
                    family_id=family.id,
                    item=item,
                )
                nutrition = None if estimate is None else estimate.nutrition

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
                ingested_count += 1
                if eligible:
                    nutrition_ready_count += 1

            menu_items.append(
                RestaurantMenuItemRead(
                    restaurant_place_id=restaurant.provider_place_id,
                    restaurant_name=restaurant.name,
                    item_name=item.name,
                    description=item.description,
                    item_price=item.price,
                    currency=item.currency,
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
                    source_reference=item.source_url,
                    catalog_key=catalog_key,
                    eligible_for_nutrition_ranking=eligible,
                )
            )
        menus.append(
            RestaurantMenuRead(
                restaurant=restaurant,
                pages_scanned=list(scraped.pages_scanned),
                items=menu_items,
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
