import json
import threading
import time
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.core.config import settings
from app.schemas.restaurant_discovery import (
    RestaurantDiscoveryPlaceRead,
    RestaurantDiscoveryRead,
)

OSM_ATTRIBUTION = "© OpenStreetMap contributors (ODbL)"
_CACHE_LOCK = threading.Lock()
_CACHE: dict[str, tuple[float, RestaurantDiscoveryRead]] = {}
_NOMINATIM_LOCK = threading.Lock()
_LAST_NOMINATIM_REQUEST_AT = 0.0


class RestaurantDiscoveryError(ValueError):
    pass


def _normalized_area(area: str) -> str:
    normalized = " ".join(area.strip().split())
    if not normalized:
        raise RestaurantDiscoveryError("Restaurant discovery requires a non-empty area.")
    return normalized


def _request_json(
    url: str,
    *,
    data: bytes | None = None,
    content_type: str | None = None,
) -> Any:
    headers = {
        "Accept": "application/json",
        "User-Agent": settings.restaurant_discovery_user_agent,
    }
    if content_type is not None:
        headers["Content-Type"] = content_type
    request = Request(url, data=data, headers=headers, method="POST" if data else "GET")
    try:
        with urlopen(  # noqa: S310 - URLs are controlled by application settings.
            request,
            timeout=settings.restaurant_discovery_timeout_seconds,
        ) as response:
            return json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RestaurantDiscoveryError("Restaurant discovery provider is unavailable.") from exc


def _nominatim_request(url: str) -> Any:
    global _LAST_NOMINATIM_REQUEST_AT
    with _NOMINATIM_LOCK:
        elapsed = time.monotonic() - _LAST_NOMINATIM_REQUEST_AT
        if elapsed < 1.0:
            time.sleep(1.0 - elapsed)
        payload = _request_json(url)
        _LAST_NOMINATIM_REQUEST_AT = time.monotonic()
        return payload


def _decimal(value: object, *, field: str) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise RestaurantDiscoveryError(
            f"Restaurant discovery provider returned an invalid {field}."
        ) from exc


def _geocode_area(area: str) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    query = urlencode(
        {
            "q": area,
            "format": "jsonv2",
            "limit": "1",
            "addressdetails": "0",
        }
    )
    base = settings.restaurant_discovery_nominatim_url.rstrip("/")
    payload = _nominatim_request(f"{base}/search?{query}")
    if not isinstance(payload, list) or not payload or not isinstance(payload[0], dict):
        raise RestaurantDiscoveryError(f"Could not locate restaurant area {area!r}.")
    bounding_box = payload[0].get("boundingbox")
    if not isinstance(bounding_box, list) or len(bounding_box) != 4:
        raise RestaurantDiscoveryError("Geocoding result does not contain a usable bounding box.")
    south, north, west, east = (
        _decimal(value, field="bounding box") for value in bounding_box
    )
    return south, west, north, east


def _overpass_query(bbox: tuple[Decimal, Decimal, Decimal, Decimal]) -> str:
    south, west, north, east = bbox
    return (
        "[out:json][timeout:20];"
        "("
        f'nwr["amenity"~"^(restaurant|fast_food|food_court)$"]'
        f"({south},{west},{north},{east});"
        ");"
        "out center tags;"
    )


def _address(tags: dict[str, object]) -> str | None:
    street = str(tags.get("addr:street") or "").strip()
    number = str(tags.get("addr:housenumber") or "").strip()
    postcode = str(tags.get("addr:postcode") or "").strip()
    city = str(tags.get("addr:city") or tags.get("addr:place") or "").strip()
    street_line = " ".join(part for part in (street, number) if part)
    locality = " ".join(part for part in (postcode, city) if part)
    result = ", ".join(part for part in (street_line, locality) if part)
    return result or None


def _coordinates(element: dict[str, object]) -> tuple[Decimal, Decimal] | None:
    lat = element.get("lat")
    lon = element.get("lon")
    if lat is None or lon is None:
        center = element.get("center")
        if not isinstance(center, dict):
            return None
        lat = center.get("lat")
        lon = center.get("lon")
    if lat is None or lon is None:
        return None
    try:
        return Decimal(str(lat)), Decimal(str(lon))
    except InvalidOperation:
        return None


def _restaurant(element: object) -> RestaurantDiscoveryPlaceRead | None:
    if not isinstance(element, dict):
        return None
    element_type = str(element.get("type") or "").strip()
    element_id = element.get("id")
    tags = element.get("tags")
    coordinates = _coordinates(element)
    if not element_type or element_id is None or not isinstance(tags, dict) or coordinates is None:
        return None
    name = str(tags.get("name") or "").strip()
    if not name:
        return None
    amenity = str(tags.get("amenity") or "restaurant").strip()
    cuisine = [
        item.strip()
        for item in str(tags.get("cuisine") or "").split(";")
        if item.strip()
    ]
    latitude, longitude = coordinates
    website = str(tags.get("contact:website") or tags.get("website") or "").strip() or None
    phone = str(tags.get("contact:phone") or tags.get("phone") or "").strip() or None
    opening_hours = str(tags.get("opening_hours") or "").strip() or None
    return RestaurantDiscoveryPlaceRead(
        provider_place_id=f"osm:{element_type}:{element_id}",
        name=name,
        cuisine=cuisine,
        amenity=amenity,
        address=_address(tags),
        latitude=latitude,
        longitude=longitude,
        website=website,
        phone=phone,
        opening_hours=opening_hours,
        source_reference=f"https://www.openstreetmap.org/{element_type}/{element_id}",
    )


def _fetch_restaurants(
    area: str,
    *,
    limit: int,
) -> RestaurantDiscoveryRead:
    bbox = _geocode_area(area)
    query = urlencode({"data": _overpass_query(bbox)}).encode("utf-8")
    payload = _request_json(
        settings.restaurant_discovery_overpass_url,
        data=query,
        content_type="application/x-www-form-urlencoded",
    )
    if not isinstance(payload, dict) or not isinstance(payload.get("elements"), list):
        raise RestaurantDiscoveryError("Restaurant discovery provider returned invalid data.")
    places = [
        place
        for element in payload["elements"]
        if (place := _restaurant(element)) is not None
    ]
    places.sort(key=lambda place: (place.name.casefold(), place.provider_place_id))
    return RestaurantDiscoveryRead(
        provider="openstreetmap",
        area=area,
        observed_at=datetime.now(UTC),
        cached=False,
        attribution=OSM_ATTRIBUTION,
        restaurants=places[:limit],
    )


def discover_restaurants(
    area: str,
    *,
    limit: int | None = None,
) -> RestaurantDiscoveryRead:
    if not settings.restaurant_discovery_enabled:
        raise RestaurantDiscoveryError("Live restaurant discovery is disabled.")
    normalized = _normalized_area(area)
    requested_limit = limit or settings.restaurant_discovery_max_results
    requested_limit = min(max(requested_limit, 1), settings.restaurant_discovery_max_results)
    cache_key = normalized.casefold()
    now = time.monotonic()
    with _CACHE_LOCK:
        cached = _CACHE.get(cache_key)
        if cached is not None and now - cached[0] <= settings.restaurant_discovery_cache_seconds:
            return cached[1].model_copy(
                update={
                    "cached": True,
                    "restaurants": cached[1].restaurants[:requested_limit],
                }
            )

    result = _fetch_restaurants(
        normalized,
        limit=settings.restaurant_discovery_max_results,
    )
    with _CACHE_LOCK:
        _CACHE[cache_key] = (time.monotonic(), result)
    return result.model_copy(update={"restaurants": result.restaurants[:requested_limit]})
