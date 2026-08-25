from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.family import Family
from app.models.meal_candidate_availability import MealCandidateAvailability, MealCommercialOffer
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


def _restaurant() -> RestaurantDiscoveryPlaceRead:
    return RestaurantDiscoveryPlaceRead(
        provider_place_id="google:place-1",
        name="Boa Mesa",
        cuisine=["portuguese"],
        amenity="restaurant",
        address="Estrada de Benfica 100, Lisboa",
        latitude=Decimal("38.7500"),
        longitude=Decimal("-9.1900"),
        website="https://boa-mesa.example/menu",
        phone=None,
        opening_hours=None,
        source_reference="https://www.google.com/maps/search/?api=1&query_place_id=place-1",
        primary_type="portuguese_restaurant",
        rating=Decimal("4.6"),
        rating_count=500,
        quality_score=Decimal("4.545"),
    )


def _discovery(provider: str) -> RestaurantDiscoveryRead:
    return RestaurantDiscoveryRead(
        provider=provider,
        area="Benfica, Lisboa",
        observed_at=datetime(2026, 8, 25, 11, 0, tzinfo=UTC),
        cached=False,
        attribution="Google Maps" if provider == "google_places" else "OpenStreetMap",
        restaurants=[_restaurant()],
    )


def test_menu_sync_refuses_osm_fallback_when_google_is_configured(
    db_session: Session,
    monkeypatch,
) -> None:
    family = _family(db_session)
    monkeypatch.setattr(restaurant_menu_sync, "google_places_configured", lambda: True)
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
    restaurant = _restaurant()
    monkeypatch.setattr(restaurant_menu_sync, "google_places_configured", lambda: True)
    monkeypatch.setattr(
        restaurant_menu_sync,
        "discover_restaurants",
        lambda area, *, limit: _discovery("google_places"),
    )
    monkeypatch.setattr(
        restaurant_menu_sync,
        "scrape_restaurant_menu",
        lambda website, *, max_items: ScrapedRestaurantMenu(
            website=website,
            pages_scanned=(website,),
            items=(
                ScrapedMenuItem(
                    name="Frango grelhado com arroz",
                    description="Frango, arroz e legumes",
                    price=Decimal("12.90"),
                    currency="EUR",
                    energy_kcal=Decimal("610"),
                    source_url=website,
                ),
            ),
        ),
    )

    result = restaurant_menu_sync.sync_restaurant_menus(
        db_session,
        family=family,
        data=RestaurantMenuSyncCreate(),
    )

    assert result.provider == "google_places"
    assert result.ingested_item_count == 1
    assert result.nutrition_ready_item_count == 1
    assert result.menus[0].restaurant == restaurant
    assert result.menus[0].items[0].energy_kcal == Decimal("610")
    assert result.menus[0].items[0].eligible_for_nutrition_ranking

    offer = db_session.scalar(select(MealCommercialOffer))
    assert offer is not None
    assert offer.source_kind == "restaurant"
    assert offer.provider_key == "restaurant_website"
    assert offer.provider_name == "Boa Mesa"
    assert offer.location == "Benfica, Lisboa"

    availability = db_session.scalar(select(MealCandidateAvailability))
    assert availability is not None
    assert availability.source_kind == "restaurant"
    assert availability.location == "Benfica, Lisboa"
