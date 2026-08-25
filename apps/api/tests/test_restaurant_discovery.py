from datetime import UTC, datetime
from decimal import Decimal

from app.schemas.restaurant_discovery import (
    RestaurantDiscoveryPlaceRead,
    RestaurantDiscoveryRead,
)
from app.services import restaurant_discovery


def _place(
    *,
    place_id: str,
    name: str,
    rating: str | None = None,
    rating_count: int | None = None,
    primary_type: str = "restaurant",
    website: str | None = None,
) -> RestaurantDiscoveryPlaceRead:
    parsed_rating = Decimal(rating) if rating is not None else None
    return RestaurantDiscoveryPlaceRead(
        provider_place_id=place_id,
        name=name,
        cuisine=[],
        amenity="fast_food" if primary_type == "fast_food_restaurant" else "restaurant",
        address="Lisboa",
        latitude=Decimal("38.75"),
        longitude=Decimal("-9.18"),
        website=website,
        phone=None,
        opening_hours=None,
        source_reference="https://example.invalid/place",
        primary_type=primary_type,
        rating=parsed_rating,
        rating_count=rating_count,
        quality_score=restaurant_discovery._quality_score(
            parsed_rating,
            rating_count,
            primary_type=primary_type,
        ),
    )


def test_osm_restaurant_parser_keeps_observed_metadata() -> None:
    parsed = restaurant_discovery._restaurant(
        {
            "type": "way",
            "id": 123,
            "center": {"lat": 38.7521, "lon": -9.1845},
            "tags": {
                "name": "Restaurante Exemplo",
                "amenity": "restaurant",
                "cuisine": "portuguese;seafood",
                "addr:street": "Rua Exemplo",
                "addr:housenumber": "12",
                "addr:postcode": "1500-000",
                "addr:city": "Lisboa",
                "website": "https://example.invalid/menu",
                "opening_hours": "Mo-Su 12:00-23:00",
            },
        }
    )

    assert parsed is not None
    assert parsed.provider_place_id == "osm:way:123"
    assert parsed.name == "Restaurante Exemplo"
    assert parsed.cuisine == ["portuguese", "seafood"]
    assert parsed.address == "Rua Exemplo 12, 1500-000 Lisboa"
    assert parsed.latitude == Decimal("38.7521")
    assert parsed.longitude == Decimal("-9.1845")
    assert parsed.website == "https://example.invalid/menu"
    assert parsed.source_reference == "https://www.openstreetmap.org/way/123"


def test_google_parser_exposes_quality_and_service_signals() -> None:
    parsed = restaurant_discovery._google_place(
        {
            "id": "place-123",
            "displayName": {"text": "Boa Mesa"},
            "formattedAddress": "Benfica, Lisboa",
            "location": {"latitude": 38.75, "longitude": -9.19},
            "primaryType": "portuguese_restaurant",
            "types": ["portuguese_restaurant", "restaurant", "food"],
            "rating": 4.7,
            "userRatingCount": 842,
            "priceLevel": "PRICE_LEVEL_MODERATE",
            "websiteUri": "https://example.invalid/menu",
            "servesLunch": True,
            "servesDinner": True,
            "delivery": False,
            "takeout": True,
        }
    )

    assert parsed is not None
    assert parsed.provider_place_id == "google:place-123"
    assert parsed.cuisine == ["portuguese"]
    assert parsed.rating == Decimal("4.7")
    assert parsed.rating_count == 842
    assert parsed.price_level == "PRICE_LEVEL_MODERATE"
    assert parsed.serves_lunch is True
    assert parsed.serves_dinner is True
    assert parsed.delivery is False
    assert parsed.takeout is True
    assert parsed.quality_score is not None


def test_apify_google_parser_preserves_menu_and_google_identity() -> None:
    parsed = restaurant_discovery._apify_place(
        {
            "title": "Boa Mesa",
            "categoryName": "Portuguese restaurant",
            "categories": ["Portuguese restaurant", "Restaurant"],
            "address": "Estrada de Benfica 100, Lisboa",
            "website": "https://boa-mesa.example/",
            "menu": "https://boa-mesa.example/ementa.pdf",
            "phone": "+351 210 000 000",
            "location": {"lat": 38.75, "lng": -9.19},
            "totalScore": 4.7,
            "reviewsCount": 842,
            "placeId": "place-123",
            "url": "https://www.google.com/maps/place/example",
            "price": "€10–20",
            "additionalInfo": {
                "Service options": [{"Delivery": False}, {"Takeout": True}],
                "Popular for": [{"Lunch": True}, {"Dinner": True}],
            },
        }
    )

    assert parsed is not None
    assert parsed.provider_place_id == "google:place-123"
    assert parsed.cuisine == ["portuguese"]
    assert parsed.menu_url == "https://boa-mesa.example/ementa.pdf"
    assert parsed.rating == Decimal("4.7")
    assert parsed.rating_count == 842
    assert parsed.delivery is False
    assert parsed.takeout is True
    assert parsed.serves_lunch is True
    assert parsed.serves_dinner is True
    assert parsed.quality_score is not None


def test_quality_score_values_review_confidence() -> None:
    established = restaurant_discovery._quality_score(
        Decimal("4.7"),
        1000,
        primary_type="portuguese_restaurant",
    )
    single_review = restaurant_discovery._quality_score(
        Decimal("5.0"),
        1,
        primary_type="restaurant",
    )

    assert established is not None
    assert single_review is not None
    assert established > single_review


def test_restaurant_ranking_prioritizes_full_service_over_fast_food() -> None:
    places = [
        _place(
            place_id="google:fast",
            name="Fast Chain",
            rating="4.9",
            rating_count=5000,
            primary_type="fast_food_restaurant",
        ),
        _place(
            place_id="google:restaurant",
            name="Boa Mesa",
            rating="4.5",
            rating_count=400,
            primary_type="portuguese_restaurant",
        ),
    ]

    ranked = restaurant_discovery._rank_and_dedupe(places)

    assert ranked[0].name == "Boa Mesa"
    assert ranked[1].name == "Fast Chain"


def test_restaurant_ranking_deduplicates_same_chain_name() -> None:
    places = [
        _place(place_id="google:1", name="100 Montaditos", rating="4.1", rating_count=200),
        _place(place_id="google:2", name="100 montaditos", rating="4.0", rating_count=800),
        _place(place_id="google:3", name="Boa Mesa", rating="4.7", rating_count=500),
    ]

    ranked = restaurant_discovery._rank_and_dedupe(places)

    assert [place.name for place in ranked].count("100 Montaditos") <= 1
    assert len([place for place in ranked if "montaditos" in place.name.casefold()]) == 1
    assert ranked[0].name == "Boa Mesa"


def test_restaurant_ranking_deduplicates_chain_website() -> None:
    places = [
        _place(
            place_id="google:1",
            name="100 Montaditos Colombo",
            rating="4.2",
            rating_count=600,
            website="https://100montaditos.example/colombo",
        ),
        _place(
            place_id="google:2",
            name="100 Montaditos Benfica",
            rating="4.4",
            rating_count=500,
            website="https://100montaditos.example/benfica",
        ),
        _place(place_id="google:3", name="Boa Mesa", rating="4.7", rating_count=500),
    ]

    ranked = restaurant_discovery._rank_and_dedupe(places)

    assert len([place for place in ranked if "montaditos" in place.name.casefold()]) == 1


def test_restaurant_discovery_caches_area_results(monkeypatch) -> None:
    restaurant_discovery._CACHE.clear()
    calls: list[str] = []

    def fake_fetch(area: str, *, limit: int) -> RestaurantDiscoveryRead:
        calls.append(area)
        return RestaurantDiscoveryRead(
            provider="openstreetmap",
            area=area,
            observed_at=datetime(2026, 8, 23, 18, 0, tzinfo=UTC),
            cached=False,
            attribution=restaurant_discovery.OSM_ATTRIBUTION,
            restaurants=[
                _place(place_id="osm:node:1", name="A"),
                _place(place_id="osm:node:2", name="B"),
            ],
        )

    monkeypatch.setattr(restaurant_discovery, "apify_google_maps_configured", lambda: False)
    monkeypatch.setattr(restaurant_discovery, "google_places_configured", lambda: False)
    monkeypatch.setattr(restaurant_discovery, "_fetch_restaurants", fake_fetch)

    first = restaurant_discovery.discover_restaurants("Benfica, Lisboa", limit=2)
    second = restaurant_discovery.discover_restaurants("  Benfica,   Lisboa ", limit=1)

    assert calls == ["Benfica, Lisboa"]
    assert not first.cached
    assert second.cached
    assert len(first.restaurants) == 2
    assert [place.name for place in second.restaurants] == ["A"]


def test_apify_google_provider_is_preferred(monkeypatch) -> None:
    restaurant_discovery._CACHE.clear()
    calls: list[str] = []

    def apify(area: str, *, limit: int) -> RestaurantDiscoveryRead:
        calls.append(area)
        return RestaurantDiscoveryRead(
            provider="google_maps_apify",
            area=area,
            observed_at=datetime(2026, 8, 25, 12, 0, tzinfo=UTC),
            cached=False,
            attribution=restaurant_discovery.APIFY_GOOGLE_ATTRIBUTION,
            restaurants=[_place(place_id="google:1", name="Boa Mesa")],
        )

    monkeypatch.setattr(restaurant_discovery, "apify_google_maps_configured", lambda: True)
    monkeypatch.setattr(restaurant_discovery, "google_places_configured", lambda: True)
    monkeypatch.setattr(restaurant_discovery, "_fetch_apify_google_restaurants", apify)

    result = restaurant_discovery.discover_restaurants("Benfica, Lisboa", limit=1)

    assert calls == ["Benfica, Lisboa"]
    assert result.provider == "google_maps_apify"
    assert result.restaurants[0].provider_place_id == "google:1"


def test_google_provider_failure_falls_back_to_osm(monkeypatch) -> None:
    restaurant_discovery._CACHE.clear()

    def fail_google(area: str, *, limit: int) -> RestaurantDiscoveryRead:
        raise restaurant_discovery.RestaurantDiscoveryError("google unavailable")

    def osm(area: str, *, limit: int) -> RestaurantDiscoveryRead:
        return RestaurantDiscoveryRead(
            provider="openstreetmap",
            area=area,
            observed_at=datetime(2026, 8, 23, 18, 0, tzinfo=UTC),
            cached=False,
            attribution=restaurant_discovery.OSM_ATTRIBUTION,
            restaurants=[_place(place_id="osm:node:1", name="Fallback")],
        )

    monkeypatch.setattr(restaurant_discovery, "apify_google_maps_configured", lambda: False)
    monkeypatch.setattr(restaurant_discovery, "google_places_configured", lambda: True)
    monkeypatch.setattr(restaurant_discovery, "_fetch_google_restaurants", fail_google)
    monkeypatch.setattr(restaurant_discovery, "_fetch_restaurants", osm)

    result = restaurant_discovery.discover_restaurants("Benfica, Lisboa", limit=1)

    assert result.provider == "openstreetmap_fallback"
    assert result.restaurants[0].name == "Fallback"
