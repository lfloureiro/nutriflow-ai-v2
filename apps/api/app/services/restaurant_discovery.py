import json
import re
import threading
import time
import unicodedata
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

from app.core.config import settings
from app.core.provider_secrets import get_provider_secret_store
from app.schemas.restaurant_discovery import (
    RestaurantDiscoveryPlaceRead,
    RestaurantDiscoveryRead,
)

OSM_ATTRIBUTION = "© OpenStreetMap contributors (ODbL)"
GOOGLE_ATTRIBUTION = "Google Maps"
APIFY_GOOGLE_ATTRIBUTION = "Google Maps via Apify"
APIFY_API_TOKEN_SECRET = "NUTRIFLOW_APIFY_API_TOKEN"
GOOGLE_PLACES_API_KEY_SECRET = "NUTRIFLOW_GOOGLE_PLACES_API_KEY"
_GOOGLE_FIELD_MASK = (
    "places.id,"
    "places.displayName,"
    "places.formattedAddress,"
    "places.location,"
    "places.primaryType,"
    "places.types,"
    "places.rating,"
    "places.userRatingCount,"
    "places.priceLevel,"
    "places.websiteUri,"
    "places.nationalPhoneNumber,"
    "places.regularOpeningHours,"
    "places.delivery,"
    "places.takeout,"
    "places.dineIn,"
    "places.servesLunch,"
    "places.servesDinner,"
    "places.servesVegetarianFood,"
    "nextPageToken"
)
_NON_BRAND_WEBSITE_HOSTS = frozenset(
    {
        "facebook.com",
        "google.com",
        "instagram.com",
        "linktr.ee",
        "thefork.pt",
        "tripadvisor.com",
    }
)
_CACHE_LOCK = threading.Lock()
_CACHE: dict[str, tuple[float, RestaurantDiscoveryRead]] = {}
_NOMINATIM_LOCK = threading.Lock()
_LAST_NOMINATIM_REQUEST_AT = 0.0


class RestaurantDiscoveryError(ValueError):
    pass


def apify_google_maps_configured() -> bool:
    return get_provider_secret_store().get(APIFY_API_TOKEN_SECRET) is not None


def google_places_configured() -> bool:
    return get_provider_secret_store().get(GOOGLE_PLACES_API_KEY_SECRET) is not None


def google_restaurant_discovery_configured() -> bool:
    apify_ready = (
        settings.restaurant_apify_google_enabled and apify_google_maps_configured()
    )
    places_ready = settings.restaurant_google_places_enabled and google_places_configured()
    return apify_ready or places_ready


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
    extra_headers: dict[str, str] | None = None,
    timeout_seconds: float | None = None,
) -> Any:
    headers = {
        "Accept": "application/json",
        "User-Agent": settings.restaurant_discovery_user_agent,
    }
    if content_type is not None:
        headers["Content-Type"] = content_type
    if extra_headers:
        headers.update(extra_headers)
    request = Request(url, data=data, headers=headers, method="POST" if data else "GET")
    try:
        with urlopen(
            request,
            timeout=timeout_seconds or settings.restaurant_discovery_timeout_seconds,
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


def _optional_decimal(value: object) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


def _optional_int(value: object) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed >= 0 else None


def _optional_bool(value: object) -> bool | None:
    return value if isinstance(value, bool) else None


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
        raise RestaurantDiscoveryError(
            "Geocoding result does not contain a usable bounding box."
        )
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


def _quality_score(
    rating: Decimal | None,
    rating_count: int | None,
    *,
    primary_type: str | None,
) -> Decimal | None:
    if rating is None:
        return None
    count = Decimal(max(rating_count or 0, 0))
    prior_rating = Decimal("4.0")
    prior_count = Decimal(50)
    score = ((rating * count) + (prior_rating * prior_count)) / (count + prior_count)
    if primary_type == "fast_food_restaurant":
        score -= Decimal("0.20")
    return max(score, Decimal(0)).quantize(Decimal("0.001"))


def _restaurant_name_key(name: str) -> str:
    normalized = unicodedata.normalize("NFKD", name.casefold())
    ascii_text = "".join(
        character
        for character in normalized
        if not unicodedata.combining(character)
    )
    return re.sub(r"[^a-z0-9]+", " ", ascii_text).strip()


def _website_identity_key(website: str | None) -> str | None:
    if not website:
        return None
    try:
        host = urlparse(website).hostname
    except ValueError:
        return None
    if not host:
        return None
    normalized = host.casefold().removeprefix("www.")
    if normalized in _NON_BRAND_WEBSITE_HOSTS:
        return None
    return normalized


def _amenity_priority(place: RestaurantDiscoveryPlaceRead) -> int:
    if place.primary_type == "fast_food_restaurant" or place.amenity == "fast_food":
        return 0
    if place.amenity == "food_court":
        return 1
    return 2


def _ranking_key(
    place: RestaurantDiscoveryPlaceRead,
) -> tuple[int, Decimal, int, Decimal, str]:
    return (
        _amenity_priority(place),
        place.quality_score if place.quality_score is not None else Decimal(-1),
        place.rating_count or 0,
        place.rating if place.rating is not None else Decimal(-1),
        place.name.casefold(),
    )


def _rank_and_dedupe(
    places: list[RestaurantDiscoveryPlaceRead],
) -> list[RestaurantDiscoveryPlaceRead]:
    ranked = sorted(places, key=_ranking_key, reverse=True)
    unique: list[RestaurantDiscoveryPlaceRead] = []
    seen_names: set[str] = set()
    seen_websites: set[str] = set()
    for place in ranked:
        name_key = _restaurant_name_key(place.name)
        website_key = _website_identity_key(place.website)
        if name_key and name_key in seen_names:
            continue
        if website_key and website_key in seen_websites:
            continue
        if name_key:
            seen_names.add(name_key)
        if website_key:
            seen_websites.add(website_key)
        unique.append(place)
    return unique


def _restaurant(element: object) -> RestaurantDiscoveryPlaceRead | None:
    if not isinstance(element, dict):
        return None
    element_type = str(element.get("type") or "").strip()
    element_id = element.get("id")
    tags = element.get("tags")
    coordinates = _coordinates(element)
    if (
        not element_type
        or element_id is None
        or not isinstance(tags, dict)
        or coordinates is None
    ):
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
    website = (
        str(tags.get("contact:website") or tags.get("website") or "").strip()
        or None
    )
    phone = str(tags.get("contact:phone") or tags.get("phone") or "").strip() or None
    opening_hours = str(tags.get("opening_hours") or "").strip() or None
    primary_type = "fast_food_restaurant" if amenity == "fast_food" else "restaurant"
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
        primary_type=primary_type,
    )


def _google_cuisine(types: object) -> list[str]:
    if not isinstance(types, list):
        return []
    cuisines: list[str] = []
    for value in types:
        if not isinstance(value, str) or not value.endswith("_restaurant"):
            continue
        if value in {"restaurant", "fast_food_restaurant"}:
            continue
        cuisines.append(value.removesuffix("_restaurant").replace("_", " "))
    return cuisines


def _google_place(place: object) -> RestaurantDiscoveryPlaceRead | None:
    if not isinstance(place, dict):
        return None
    place_id = str(place.get("id") or "").strip()
    display_name = place.get("displayName")
    location = place.get("location")
    if (
        not place_id
        or not isinstance(display_name, dict)
        or not isinstance(location, dict)
    ):
        return None
    name = str(display_name.get("text") or "").strip()
    latitude = _optional_decimal(location.get("latitude"))
    longitude = _optional_decimal(location.get("longitude"))
    if not name or latitude is None or longitude is None:
        return None

    primary_type = str(place.get("primaryType") or "").strip() or None
    rating = _optional_decimal(place.get("rating"))
    rating_count = _optional_int(place.get("userRatingCount"))
    opening = place.get("regularOpeningHours")
    weekday_descriptions = (
        opening.get("weekdayDescriptions") if isinstance(opening, dict) else None
    )
    opening_hours = (
        " · ".join(str(item) for item in weekday_descriptions)
        if isinstance(weekday_descriptions, list)
        else None
    )
    amenity = "fast_food" if primary_type == "fast_food_restaurant" else "restaurant"
    return RestaurantDiscoveryPlaceRead(
        provider_place_id=f"google:{place_id}",
        name=name,
        cuisine=_google_cuisine(place.get("types")),
        amenity=amenity,
        address=str(place.get("formattedAddress") or "").strip() or None,
        latitude=latitude,
        longitude=longitude,
        website=str(place.get("websiteUri") or "").strip() or None,
        phone=str(place.get("nationalPhoneNumber") or "").strip() or None,
        opening_hours=opening_hours,
        source_reference=(
            "https://www.google.com/maps/search/?api=1&query_place_id=" + place_id
        ),
        primary_type=primary_type,
        rating=rating,
        rating_count=rating_count,
        price_level=str(place.get("priceLevel") or "").strip() or None,
        delivery=_optional_bool(place.get("delivery")),
        takeout=_optional_bool(place.get("takeout")),
        dine_in=_optional_bool(place.get("dineIn")),
        serves_lunch=_optional_bool(place.get("servesLunch")),
        serves_dinner=_optional_bool(place.get("servesDinner")),
        serves_vegetarian_food=_optional_bool(place.get("servesVegetarianFood")),
        quality_score=_quality_score(
            rating,
            rating_count,
            primary_type=primary_type,
        ),
    )


def _apify_opening_hours(value: object) -> str | None:
    if isinstance(value, dict):
        parts = [f"{day}: {hours}" for day, hours in value.items() if hours]
        return " · ".join(parts) or None
    if isinstance(value, list):
        parts: list[str] = []
        for item in value:
            if isinstance(item, str) and item.strip():
                parts.append(item.strip())
            elif isinstance(item, dict):
                day = str(item.get("day") or "").strip()
                hours = str(item.get("hours") or "").strip()
                text = ": ".join(part for part in (day, hours) if part)
                if text:
                    parts.append(text)
        return " · ".join(parts) or None
    return str(value).strip() or None if value is not None else None


def _apify_info_flag(place: dict[str, object], *labels: str) -> bool | None:
    additional = place.get("additionalInfo")
    if not isinstance(additional, dict):
        return None
    wanted = {label.casefold() for label in labels}
    for entries in additional.values():
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            for key, value in entry.items():
                if key.casefold() in wanted and isinstance(value, bool):
                    return value
    return None


def _apify_primary_type(category_name: str) -> str:
    normalized = category_name.strip().casefold()
    if "fast food" in normalized:
        return "fast_food_restaurant"
    if normalized.endswith(" restaurant"):
        return normalized.replace(" ", "_")
    return "restaurant"


def _apify_cuisine(place: dict[str, object]) -> list[str]:
    raw_categories = place.get("categories")
    categories = raw_categories if isinstance(raw_categories, list) else []
    category_name = str(place.get("categoryName") or "").strip()
    if category_name:
        categories = [category_name, *categories]

    cuisines: list[str] = []
    seen: set[str] = set()
    excluded = {"restaurant", "fast food restaurant", "delivery restaurant"}
    for raw in categories:
        if not isinstance(raw, str):
            continue
        normalized = raw.strip().casefold()
        if normalized in excluded or not normalized.endswith(" restaurant"):
            continue
        cuisine = normalized.removesuffix(" restaurant")
        if cuisine and cuisine not in seen:
            seen.add(cuisine)
            cuisines.append(cuisine)
    return cuisines


def _apify_place(place: object) -> RestaurantDiscoveryPlaceRead | None:
    if not isinstance(place, dict):
        return None
    if place.get("permanentlyClosed") is True or place.get("temporarilyClosed") is True:
        return None

    place_id = str(place.get("placeId") or "").strip()
    name = str(place.get("title") or "").strip()
    location = place.get("location")
    if not place_id or not name or not isinstance(location, dict):
        return None
    latitude = _optional_decimal(location.get("lat"))
    longitude = _optional_decimal(location.get("lng"))
    if latitude is None or longitude is None:
        return None

    category_name = str(place.get("categoryName") or "Restaurant").strip()
    primary_type = _apify_primary_type(category_name)
    rating = _optional_decimal(place.get("totalScore"))
    rating_count = _optional_int(place.get("reviewsCount"))
    source_reference = str(place.get("url") or "").strip()
    if not source_reference:
        source_reference = (
            "https://www.google.com/maps/search/?api=1&query_place_id=" + place_id
        )
    return RestaurantDiscoveryPlaceRead(
        provider_place_id=f"google:{place_id}",
        name=name,
        cuisine=_apify_cuisine(place),
        amenity=(
            "fast_food" if primary_type == "fast_food_restaurant" else "restaurant"
        ),
        address=str(place.get("address") or "").strip() or None,
        latitude=latitude,
        longitude=longitude,
        website=str(place.get("website") or "").strip() or None,
        menu_url=str(place.get("menu") or "").strip() or None,
        phone=str(place.get("phone") or "").strip() or None,
        opening_hours=_apify_opening_hours(place.get("openingHours")),
        source_reference=source_reference,
        primary_type=primary_type,
        rating=rating,
        rating_count=rating_count,
        price_level=str(place.get("price") or place.get("priceLevel") or "").strip()
        or None,
        delivery=_apify_info_flag(place, "Delivery"),
        takeout=_apify_info_flag(place, "Takeout", "Takeaway"),
        dine_in=_apify_info_flag(place, "Dine-in", "Dine in"),
        serves_lunch=_apify_info_flag(place, "Lunch"),
        serves_dinner=_apify_info_flag(place, "Dinner"),
        quality_score=_quality_score(
            rating,
            rating_count,
            primary_type=primary_type,
        ),
    )


def _fetch_apify_google_restaurants(
    area: str,
    *,
    limit: int,
) -> RestaurantDiscoveryRead:
    token = get_provider_secret_store().get(APIFY_API_TOKEN_SECRET)
    if token is None:
        raise RestaurantDiscoveryError(
            "Apify Google Maps restaurant discovery is not configured."
        )
    payload = {
        "searchStringsArray": ["restaurant"],
        "locationQuery": area,
        "maxCrawledPlacesPerSearch": limit,
        "language": "en",
        "scrapeSocialMediaProfiles": {
            "facebooks": False,
            "instagrams": False,
            "youtubes": False,
            "tiktoks": False,
            "twitters": False,
        },
        "maximumLeadsEnrichmentRecords": 0,
        "maxImages": 0,
    }
    response = _request_json(
        settings.restaurant_apify_google_url,
        data=json.dumps(payload).encode("utf-8"),
        content_type="application/json",
        extra_headers={"Authorization": f"Bearer {token}"},
        timeout_seconds=settings.restaurant_apify_timeout_seconds,
    )
    if not isinstance(response, list):
        raise RestaurantDiscoveryError("Apify Google Maps returned invalid restaurant data.")
    places = [
        parsed for raw in response if (parsed := _apify_place(raw)) is not None
    ]
    ranked = _rank_and_dedupe(places)
    return RestaurantDiscoveryRead(
        provider="google_maps_apify",
        area=area,
        observed_at=datetime.now(UTC),
        cached=False,
        attribution=APIFY_GOOGLE_ATTRIBUTION,
        restaurants=ranked[:limit],
    )


def _fetch_google_restaurants(
    area: str,
    *,
    limit: int,
) -> RestaurantDiscoveryRead:
    api_key = get_provider_secret_store().get(GOOGLE_PLACES_API_KEY_SECRET)
    if api_key is None:
        raise RestaurantDiscoveryError("Google Places restaurant discovery is not configured.")

    places: list[RestaurantDiscoveryPlaceRead] = []
    page_token: str | None = None
    while len(places) < limit:
        payload: dict[str, object] = {
            "textQuery": f"restaurants in {area}",
            "pageSize": min(20, max(limit - len(places), 1)),
        }
        if page_token is not None:
            payload["pageToken"] = page_token
        response = _request_json(
            settings.restaurant_google_places_url,
            data=json.dumps(payload).encode("utf-8"),
            content_type="application/json",
            extra_headers={
                "X-Goog-Api-Key": api_key,
                "X-Goog-FieldMask": _GOOGLE_FIELD_MASK,
            },
        )
        if not isinstance(response, dict):
            raise RestaurantDiscoveryError(
                "Google Places returned invalid restaurant data."
            )
        raw_places = response.get("places")
        if raw_places is None:
            raw_places = []
        if not isinstance(raw_places, list):
            raise RestaurantDiscoveryError(
                "Google Places returned invalid restaurant data."
            )
        places.extend(
            parsed
            for raw in raw_places
            if (parsed := _google_place(raw)) is not None
        )
        next_token = response.get("nextPageToken")
        page_token = str(next_token).strip() if next_token else None
        if page_token is None or not raw_places:
            break

    ranked = _rank_and_dedupe(places)
    return RestaurantDiscoveryRead(
        provider="google_places",
        area=area,
        observed_at=datetime.now(UTC),
        cached=False,
        attribution=GOOGLE_ATTRIBUTION,
        restaurants=ranked[:limit],
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
    ranked = _rank_and_dedupe(places)
    return RestaurantDiscoveryRead(
        provider="openstreetmap",
        area=area,
        observed_at=datetime.now(UTC),
        cached=False,
        attribution=OSM_ATTRIBUTION,
        restaurants=ranked[:limit],
    )


def _live_provider_key() -> str:
    if settings.restaurant_apify_google_enabled and apify_google_maps_configured():
        return "google_maps_apify"
    if settings.restaurant_google_places_enabled and google_places_configured():
        return "google_places"
    return "openstreetmap"


def _cache_ttl(result: RestaurantDiscoveryRead) -> int:
    if result.provider == "openstreetmap_fallback":
        return min(settings.restaurant_discovery_cache_seconds, 300)
    return settings.restaurant_discovery_cache_seconds


def _google_fallback_or_osm(area: str) -> RestaurantDiscoveryRead:
    if settings.restaurant_google_places_enabled and google_places_configured():
        try:
            return _fetch_google_restaurants(
                area,
                limit=settings.restaurant_discovery_max_results,
            )
        except RestaurantDiscoveryError:
            pass
    return _fetch_restaurants(
        area,
        limit=settings.restaurant_discovery_max_results,
    ).model_copy(update={"provider": "openstreetmap_fallback"})


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
    provider_key = _live_provider_key()
    cache_key = f"{provider_key}:{normalized.casefold()}"
    now = time.monotonic()
    with _CACHE_LOCK:
        cached = _CACHE.get(cache_key)
        if cached is not None and now - cached[0] <= _cache_ttl(cached[1]):
            return cached[1].model_copy(
                update={
                    "cached": True,
                    "restaurants": cached[1].restaurants[:requested_limit],
                }
            )

    result: RestaurantDiscoveryRead
    if provider_key == "google_maps_apify":
        try:
            result = _fetch_apify_google_restaurants(
                normalized,
                limit=settings.restaurant_discovery_max_results,
            )
        except RestaurantDiscoveryError:
            result = _google_fallback_or_osm(normalized)
    elif provider_key == "google_places":
        try:
            result = _fetch_google_restaurants(
                normalized,
                limit=settings.restaurant_discovery_max_results,
            )
        except RestaurantDiscoveryError:
            result = _fetch_restaurants(
                normalized,
                limit=settings.restaurant_discovery_max_results,
            ).model_copy(update={"provider": "openstreetmap_fallback"})
    else:
        result = _fetch_restaurants(
            normalized,
            limit=settings.restaurant_discovery_max_results,
        )

    with _CACHE_LOCK:
        _CACHE[cache_key] = (time.monotonic(), result)
    return result.model_copy(update={"restaurants": result.restaurants[:requested_limit]})
