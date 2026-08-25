from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.family import Family
from app.models.meal_candidate_availability import MealCandidateAvailability, MealCommercialOffer
from app.providers.meal_delivery import MealDeliveryDiscoveryRequest
from app.schemas.external_menu import ExternalMenuItemObservationWrite
from app.schemas.restaurant_discovery import RestaurantDiscoveryPlaceRead, RestaurantDiscoveryRead
from app.schemas.restaurant_menu_sync import RestaurantMenuSyncCreate
from app.services import restaurant_menu_sync
from app.services.restaurant_menu_scraper import ScrapedMenuItem, ScrapedRestaurantMenu


def _family(db_session: Session) -> Family:
    family = Family(
        name="Família Restaurante",
        timezone="Europe/Lisbon",
        restaurant_area="Benfica, Lisboa",
        meal_discovery_sources=["shared_recipes", "restaurants"],
    )
    db_session.add(family)
    db_session.flush()
    return family


def _restaurant(*, menu_url: str | None = None) -> RestaurantDiscoveryPlaceRead:
    return RestaurantDiscoveryPlaceRead(
        provider_place_id="google:place-1",
        name="Boa Mesa",
        cuisine=["portuguese"],
        amenity="restaurant",
        address="Estrada de Benfica 100, Lisboa",
        latitude=Decimal("38.7500"),
        longitude=Decimal("-9.1900"),
        website="https://boa-mesa.example/",
        menu_url=menu_url,
        phone=None,
        opening_hours=None,
        source_reference="https://www.google.com/maps/search/?api=1&query_place_id=place-1",
        primary_type="portuguese_restaurant",
        rating=Decimal("4.6"),
        rating_count=500,
        quality_score=Decimal("4.545"),
    )


def _discovery(
    provider: str,
    *,
    restaurant: RestaurantDiscoveryPlaceRead | None = None,
) -> RestaurantDiscoveryRead:
    google_provider = provider in {"google_places", "google_maps_apify"}
    return RestaurantDiscoveryRead(
        provider=provider,
        area="Benfica, Lisboa",
        observed_at=datetime(2026, 8, 25, 11, 0, tzinfo=UTC),
        cached=False,
        attribution="Google Maps" if google_provider else "OpenStreetMap",
        restaurants=[restaurant or _restaurant()],
    )


class FakeUberMenuAdapter:
    provider_key = "uber_eats"

    def discover_menu_items(
        self,
        request: MealDeliveryDiscoveryRequest,
    ) -> tuple[ExternalMenuItemObservationWrite, ...]:
        assert request.query == "Boa Mesa"
        assert request.delivery_address == "Benfica, Lisboa"
        return (
            ExternalMenuItemObservationWrite(
                provider_key="uber_eats",
                provider_name="Uber Eats",
                merchant_key="boa-mesa",
                merchant_name="Restaurante Boa Mesa",
                item_key="dish-1",
                item_name="Frango grelhado com arroz",
                description="Frango, arroz e legumes",
                source_kind="delivery",
                location=request.delivery_address,
                item_price=Decimal("12.90"),
                currency="EUR",
                observed_at=datetime(2026, 8, 25, 11, 0, tzinfo=UTC),
                source_reference="https://www.ubereats.com/store/boa-mesa#dish-1",
            ),
        )


def test_menu_sync_refuses_osm_fallback_when_google_is_configured(
    db_session: Session,
    monkeypatch,
) -> None:
    family = _family(db_session)
    monkeypatch.setattr(
        restaurant_menu_sync,
        "google_restaurant_discovery_configured",
        lambda: True,
    )
    monkeypatch.setattr(
        restaurant_menu_sync,
        "discover_restaurants",
        lambda area, *, limit: _discovery("openstreetmap_fallback"),
    )

    with pytest.raises(
        restaurant_menu_sync.RestaurantMenuSyncError,
        match="will not mix OpenStreetMap fallback",
    ):
        restaurant_menu_sync.sync_restaurant_menus(
            db_session,
            family=family,
            data=RestaurantMenuSyncCreate(),
        )


def test_google_menu_sync_ingests_real_dish_offer_for_recommendations(
    db_session: Session,
    monkeypatch,
) -> None:
    family = _family(db_session)
    restaurant = _restaurant(menu_url="https://boa-mesa.example/ementa.pdf")
    monkeypatch.setattr(
        restaurant_menu_sync,
        "google_restaurant_discovery_configured",
        lambda: True,
    )
    monkeypatch.setattr(
        restaurant_menu_sync,
        "discover_restaurants",
        lambda area, *, limit: _discovery(
            "google_maps_apify",
            restaurant=restaurant,
        ),
    )
    scraped_sources: list[str] = []

    def scrape(source: str, *, max_items: int) -> ScrapedRestaurantMenu:
        scraped_sources.append(source)
        return ScrapedRestaurantMenu(
            website=source,
            pages_scanned=(source,),
            items=(
                ScrapedMenuItem(
                    name="Frango grelhado com arroz",
                    description="Frango, arroz e legumes",
                    price=Decimal("12.90"),
                    currency="EUR",
                    energy_kcal=Decimal(610),
                    source_url=source,
                ),
            ),
        )

    monkeypatch.setattr(restaurant_menu_sync, "scrape_restaurant_menu", scrape)

    result = restaurant_menu_sync.sync_restaurant_menus(
        db_session,
        family=family,
        data=RestaurantMenuSyncCreate(),
    )

    assert result.provider == "google_maps_apify"
    assert scraped_sources == ["https://boa-mesa.example/ementa.pdf"]
    assert result.ingested_item_count == 1
    assert result.nutrition_ready_item_count == 1
    assert result.menus[0].restaurant == restaurant
    assert result.menus[0].items[0].energy_kcal == Decimal(610)
    assert result.menus[0].items[0].eligible_for_nutrition_ranking

    offer = db_session.scalar(select(MealCommercialOffer))
    assert offer is not None
    assert offer.provider_key == "restaurant_website"
    assert offer.provider_name == "Boa Mesa"

    availability = db_session.scalar(select(MealCandidateAvailability))
    assert availability is not None
    assert availability.source_kind == "restaurant"
    assert availability.location == "Benfica, Lisboa"


def test_google_menu_sync_falls_back_to_delivery_marketplace_menu(
    db_session: Session,
    monkeypatch,
) -> None:
    family = _family(db_session)
    family.meal_discovery_sources = ["shared_recipes", "restaurants", "uber_eats"]
    family.delivery_address = "Benfica, Lisboa"
    restaurant = _restaurant().model_copy(update={"website": None, "menu_url": None})

    monkeypatch.setattr(
        restaurant_menu_sync,
        "google_restaurant_discovery_configured",
        lambda: True,
    )
    monkeypatch.setattr(
        restaurant_menu_sync,
        "discover_restaurants",
        lambda area, *, limit: _discovery(
            "google_maps_apify",
            restaurant=restaurant,
        ),
    )
    monkeypatch.setattr(
        restaurant_menu_sync,
        "get_registered_meal_delivery_adapter",
        lambda provider_key: (
            FakeUberMenuAdapter() if provider_key == "uber_eats" else None
        ),
    )
    monkeypatch.setattr(
        restaurant_menu_sync,
        "get_meal_delivery_provider_integration",
        lambda provider_key, *, adapter_available: SimpleNamespace(live=True),
    )

    result = restaurant_menu_sync.sync_restaurant_menus(
        db_session,
        family=family,
        data=RestaurantMenuSyncCreate(),
    )

    assert result.ingested_item_count == 1
    assert result.menus[0].error is None
    assert result.menus[0].pages_scanned[0] == "delivery:uber_eats"
    item = result.menus[0].items[0]
    assert item.restaurant_name == "Boa Mesa"
    assert item.item_name == "Frango grelhado com arroz"
    assert item.item_price == Decimal("12.90")
    assert "ubereats.com" in item.source_reference

    offer = db_session.scalar(select(MealCommercialOffer))
    assert offer is not None
    assert offer.provider_key == "uber_eats"
    assert offer.provider_name == "Uber Eats"
