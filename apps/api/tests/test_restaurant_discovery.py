from datetime import UTC, datetime
from decimal import Decimal

from app.schemas.restaurant_discovery import RestaurantDiscoveryRead
from app.services import restaurant_discovery


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
                restaurant_discovery.RestaurantDiscoveryPlaceRead(
                    provider_place_id="osm:node:1",
                    name="A",
                    cuisine=["portuguese"],
                    amenity="restaurant",
                    address="Lisboa",
                    latitude=Decimal("38.75"),
                    longitude=Decimal("-9.18"),
                    website=None,
                    phone=None,
                    opening_hours=None,
                    source_reference="https://www.openstreetmap.org/node/1",
                ),
                restaurant_discovery.RestaurantDiscoveryPlaceRead(
                    provider_place_id="osm:node:2",
                    name="B",
                    cuisine=[],
                    amenity="restaurant",
                    address="Lisboa",
                    latitude=Decimal("38.76"),
                    longitude=Decimal("-9.19"),
                    website=None,
                    phone=None,
                    opening_hours=None,
                    source_reference="https://www.openstreetmap.org/node/2",
                ),
            ],
        )

    monkeypatch.setattr(restaurant_discovery, "_fetch_restaurants", fake_fetch)

    first = restaurant_discovery.discover_restaurants("Benfica, Lisboa", limit=2)
    second = restaurant_discovery.discover_restaurants("  Benfica,   Lisboa ", limit=1)

    assert calls == ["Benfica, Lisboa"]
    assert not first.cached
    assert second.cached
    assert len(first.restaurants) == 2
    assert [place.name for place in second.restaurants] == ["A"]
