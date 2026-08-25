import hashlib
import json
import re
import unicodedata
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from difflib import SequenceMatcher
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen

from app.core.config import settings
from app.core.provider_secrets import get_provider_secret_store
from app.providers.meal_delivery import MealDeliveryDiscoveryRequest
from app.schemas.external_menu import ExternalMenuItemObservationWrite

APIFY_API_TOKEN_SECRET = "NUTRIFLOW_APIFY_API_TOKEN"
_VALIDITY = timedelta(hours=6)
_PRICE_RE = re.compile(r"(?P<value>\d+(?:[.,]\d{1,2})?)")


class ApifyDeliveryProviderError(RuntimeError):
    pass


def apify_delivery_configured() -> bool:
    return (
        settings.meal_delivery_apify_enabled
        and get_provider_secret_store().get(APIFY_API_TOKEN_SECRET) is not None
    )


def _actor_request(url: str, payload: dict[str, object]) -> list[object]:
    token = get_provider_secret_store().get(APIFY_API_TOKEN_SECRET)
    if token is None:
        raise ApifyDeliveryProviderError(
            "Delivery marketplace discovery requires NUTRIFLOW_APIFY_API_TOKEN."
        )
    separator = "&" if "?" in url else "?"
    request = Request(
        f"{url}{separator}token={quote(token, safe='')}",
        data=json.dumps(payload).encode(),
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "NutriFlowAI/0.1 delivery-discovery",
        },
        method="POST",
    )
    try:
        with urlopen(
            request,
            timeout=settings.meal_delivery_apify_timeout_seconds,
        ) as response:
            raw = json.loads(response.read().decode())
    except HTTPError as exc:
        detail = ""
        try:
            detail = " ".join(exc.read().decode(errors="replace").split())[:500]
        except OSError:
            detail = ""
        suffix = f" {detail}" if detail else ""
        raise ApifyDeliveryProviderError(
            f"Delivery marketplace provider returned HTTP {exc.code}.{suffix}"
        ) from exc
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise ApifyDeliveryProviderError(
            "Delivery marketplace provider is unavailable."
        ) from exc
    if not isinstance(raw, list):
        raise ApifyDeliveryProviderError(
            "Delivery marketplace provider returned invalid data."
        )
    return raw


def _text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = " ".join(value.split())
    return normalized or None


def _decimal(value: object) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return Decimal(str(value).replace(",", "."))
    except (InvalidOperation, ValueError):
        return None


def _display_price(value: object) -> Decimal | None:
    text = _text(value)
    if text is None:
        return None
    match = _PRICE_RE.search(text)
    return None if match is None else _decimal(match.group("value"))


def _uber_price(item: dict[str, object]) -> Decimal | None:
    display = _display_price(item.get("priceTagline"))
    if display is not None:
        return display
    raw = _decimal(item.get("price"))
    if raw is None:
        return None
    if raw >= 100:
        return raw / Decimal(100)
    return raw


def _fee(value: object) -> Decimal | None:
    if isinstance(value, dict):
        for key in ("value", "amount", "price"):
            parsed = _decimal(value.get(key))
            if parsed is not None:
                return parsed / Decimal(100) if parsed >= 100 else parsed
        for key in ("text", "display", "priceTagline"):
            parsed = _display_price(value.get(key))
            if parsed is not None:
                return parsed
        return None
    parsed = _display_price(value)
    if parsed is not None:
        return parsed
    return _decimal(value)


def _stable_key(*parts: str) -> str:
    return hashlib.sha256("\x1f".join(parts).encode()).hexdigest()[:48]


def _source_reference(url: str, item_key: str) -> str:
    return f"{url}#item-{item_key}"[:255]


def _normalize_name(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.casefold())
    ascii_text = "".join(
        character for character in normalized if not unicodedata.combining(character)
    )
    words = re.findall(r"[a-z0-9]+", ascii_text)
    ignored = {
        "restaurante",
        "restaurant",
        "cc",
        "c",
        "centro",
        "comercial",
        "lisboa",
        "lisbon",
    }
    return " ".join(word for word in words if word not in ignored)


def _merchant_matches(query: str, merchant_name: str) -> bool:
    expected = _normalize_name(query)
    actual = _normalize_name(merchant_name)
    if not expected or not actual:
        return False
    if expected in actual or actual in expected:
        return True
    return SequenceMatcher(None, expected, actual).ratio() >= 0.78


def _uber_store_is_portuguese(raw_store: dict[str, object]) -> bool:
    currency = (_text(raw_store.get("currencyCode")) or "").upper()
    location = raw_store.get("location")
    country = None
    if isinstance(location, dict):
        country = (_text(location.get("country")) or "").upper()
    if country and country != "PT":
        return False
    return not (currency and currency != "EUR")


def _uber_rows(
    payload: list[object],
    *,
    request: MealDeliveryDiscoveryRequest,
) -> tuple[ExternalMenuItemObservationWrite, ...]:
    observed_at = datetime.now(UTC)
    results: list[ExternalMenuItemObservationWrite] = []
    seen_items: set[tuple[str, str]] = set()
    for raw_store in payload:
        if not isinstance(raw_store, dict) or not _uber_store_is_portuguese(raw_store):
            continue
        merchant_name = _text(raw_store.get("title") or raw_store.get("sanitizedTitle"))
        url = _text(raw_store.get("url"))
        if merchant_name is None or url is None:
            continue
        if request.query and not _merchant_matches(request.query, merchant_name):
            continue
        merchant_key = _text(raw_store.get("uuid")) or _stable_key(url, merchant_name)
        currency = (_text(raw_store.get("currencyCode")) or "EUR").upper()[:3]
        delivery_fee = _fee(
            raw_store.get("deliveryFee")
            or raw_store.get("deliveryFeeValue")
            or raw_store.get("deliveryFeeTagline")
            or raw_store.get("fareBadge")
        )
        menu = raw_store.get("menu")
        if not isinstance(menu, list):
            continue
        for raw_section in menu:
            if not isinstance(raw_section, dict):
                continue
            items = raw_section.get("catalogItems") or raw_section.get("items")
            if not isinstance(items, list):
                continue
            for raw_item in items:
                if not isinstance(raw_item, dict):
                    continue
                if raw_item.get("isSoldOut") is True or raw_item.get("isAvailable") is False:
                    continue
                item_name = _text(raw_item.get("title") or raw_item.get("name"))
                price = _uber_price(raw_item)
                if item_name is None or price is None:
                    continue
                item_key = _text(raw_item.get("uuid") or raw_item.get("id")) or _stable_key(
                    merchant_key,
                    item_name,
                )
                dedupe_key = (merchant_key, item_key)
                if dedupe_key in seen_items:
                    continue
                seen_items.add(dedupe_key)
                results.append(
                    ExternalMenuItemObservationWrite(
                        provider_key="uber_eats",
                        provider_name="Uber Eats",
                        merchant_key=merchant_key[:160],
                        merchant_name=merchant_name[:160],
                        item_key=item_key[:160],
                        item_name=item_name[:160],
                        description=_text(
                            raw_item.get("itemDescription") or raw_item.get("description")
                        ),
                        source_kind="delivery",
                        location=request.delivery_address[:160],
                        item_price=price,
                        currency=currency,
                        delivery_fee=delivery_fee,
                        minimum_order=None,
                        observed_at=observed_at,
                        valid_until=observed_at + _VALIDITY,
                        source_reference=_source_reference(url, item_key),
                    )
                )
                if len(results) >= request.limit:
                    return tuple(results)
    return tuple(results)


def _city_from_address(address: str) -> str:
    normalized = " ".join(address.split())
    lower = normalized.casefold()
    if "lisboa" in lower or "lisbon" in lower:
        return "Lisboa"
    parts = [part.strip() for part in normalized.split(",") if part.strip()]
    return parts[-1] if parts else normalized


def _organic_results(payload: list[object]) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    for row in payload:
        if not isinstance(row, dict):
            continue
        if row.get("type") == "organic":
            results.append(row)
        nested = row.get("organicResults")
        if isinstance(nested, list):
            results.extend(item for item in nested if isinstance(item, dict))
    return results


def _uber_store_urls_from_google(
    payload: list[object],
    *,
    query: str,
) -> tuple[str, ...]:
    candidates: list[tuple[int, str]] = []
    seen: set[str] = set()
    for row in _organic_results(payload):
        url = _text(row.get("url") or row.get("link"))
        title = _text(row.get("title")) or ""
        if url is None or url in seen:
            continue
        parsed = urlparse(url)
        if parsed.hostname not in {"www.ubereats.com", "ubereats.com"}:
            continue
        if "/pt/store/" not in parsed.path and "/pt-en/store/" not in parsed.path:
            continue
        if not _merchant_matches(query, title):
            continue
        seen.add(url)
        normalized_title = _normalize_name(title)
        normalized_query = _normalize_name(query)
        score = 2 if normalized_query and normalized_query in normalized_title else 1
        candidates.append((score, url))
    candidates.sort(key=lambda item: item[0], reverse=True)
    return tuple(url for _, url in candidates[:3])


def _resolve_uber_store_urls(query: str, delivery_address: str) -> tuple[str, ...]:
    city = _city_from_address(delivery_address)
    payload = _actor_request(
        settings.nutrition_apify_google_search_url,
        {
            "queries": f'site:ubereats.com/pt/store "{query}" {city}',
            "maxPagesPerQuery": 1,
            "countryCode": "pt",
            "searchLanguage": "pt",
            "languageCode": "pt-PT",
            "includeUnfilteredResults": False,
            "saveHtml": False,
            "saveHtmlToKeyValueStore": False,
        },
    )
    return _uber_store_urls_from_google(payload, query=query)


def _glovo_rows(
    payload: list[object],
    *,
    request: MealDeliveryDiscoveryRequest,
) -> tuple[ExternalMenuItemObservationWrite, ...]:
    stores: dict[str, dict[str, object]] = {}
    for row in payload:
        if not isinstance(row, dict) or row.get("recordType") != "store":
            continue
        slug = _text(row.get("slug"))
        if slug:
            stores[slug] = row

    query = (request.query or "").strip().casefold()
    observed_at = datetime.now(UTC)
    results: list[ExternalMenuItemObservationWrite] = []
    for row in payload:
        if not isinstance(row, dict) or row.get("recordType") != "product":
            continue
        merchant_name = _text(row.get("storeName"))
        item_name = _text(row.get("name"))
        price = _decimal(row.get("price"))
        if merchant_name is None or item_name is None or price is None:
            continue
        if query and query not in merchant_name.casefold() and query not in item_name.casefold():
            continue
        slug = _text(row.get("storeSlug")) or _stable_key(merchant_name)
        store = stores.get(slug, {})
        url = _text(store.get("url")) or (
            f"https://glovoapp.com/pt/pt/lisboa/stores/{slug}"
        )
        item_key = _text(row.get("productId")) or _stable_key(slug, item_name)
        results.append(
            ExternalMenuItemObservationWrite(
                provider_key="glovo",
                provider_name="Glovo",
                merchant_key=slug[:160],
                merchant_name=merchant_name[:160],
                item_key=item_key[:160],
                item_name=item_name[:160],
                description=_text(row.get("description")),
                source_kind="delivery",
                location=request.delivery_address[:160],
                item_price=price,
                currency=(_text(row.get("currency")) or "EUR").upper()[:3],
                delivery_fee=_fee(store.get("deliveryFeeEffective")),
                minimum_order=None,
                observed_at=observed_at,
                valid_until=observed_at + _VALIDITY,
                source_reference=_source_reference(url, item_key),
            )
        )
        if len(results) >= request.limit:
            return tuple(results)
    return tuple(results)


class UberEatsApifyAdapter:
    provider_key = "uber_eats"

    def discover_menu_items(
        self,
        request: MealDeliveryDiscoveryRequest,
    ) -> tuple[ExternalMenuItemObservationWrite, ...]:
        max_stores = max(1, min(settings.meal_delivery_apify_max_stores, 20))
        payload = _actor_request(
            settings.uber_eats_apify_url,
            {
                "locale": "pt-PT",
                "addressCountry": "PT",
                "address": request.delivery_address,
                "query": request.query or "",
                "storeType": "RESTAURANTS",
                "maxRows": max_stores,
                "getMenuCustomizations": False,
            },
        )
        observations = _uber_rows(payload, request=request)
        if observations or not request.query:
            return observations

        store_urls = _resolve_uber_store_urls(request.query, request.delivery_address)
        if not store_urls:
            return ()
        direct_payload = _actor_request(
            settings.uber_eats_apify_url,
            {
                "locale": "pt-PT",
                "addressCountry": "PT",
                "urls": list(store_urls),
                "maxRows": min(len(store_urls), max_stores),
                "getMenuCustomizations": False,
            },
        )
        return _uber_rows(direct_payload, request=request)


class GlovoApifyAdapter:
    provider_key = "glovo"

    def discover_menu_items(
        self,
        request: MealDeliveryDiscoveryRequest,
    ) -> tuple[ExternalMenuItemObservationWrite, ...]:
        payload = _actor_request(
            settings.glovo_apify_url,
            {
                "city": _city_from_address(request.delivery_address),
                "storeCategory": "food",
                "categoryFilters": [],
                "storeUrls": [],
                "includeProducts": True,
                "maxStores": max(1, min(settings.meal_delivery_apify_max_stores, 20)),
                "language": "pt",
            },
        )
        return _glovo_rows(payload, request=request)
