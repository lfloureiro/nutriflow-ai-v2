import json
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from app.core.config import settings
from app.core.provider_secrets import get_provider_secret_store

APIFY_API_TOKEN_SECRET = "NUTRIFLOW_APIFY_API_TOKEN"
_KCAL_PATTERN = re.compile(r"(?<!\d)(\d{2,4}(?:[.,]\d+)?)\s*kcal\b", re.IGNORECASE)


class RecipeEvidenceSearchError(ValueError):
    pass


@dataclass(frozen=True)
class CalorieMention:
    energy_kcal: Decimal
    basis: str
    context: str


@dataclass(frozen=True)
class RecipeEvidenceSearchHit:
    title: str
    url: str
    description: str | None
    position: int | None
    calorie_mentions: tuple[CalorieMention, ...]


@dataclass(frozen=True)
class RecipeEvidenceSearchResult:
    recipe_name: str
    query: str
    hits: tuple[RecipeEvidenceSearchHit, ...]


def nutrition_web_evidence_configured() -> bool:
    return (
        settings.nutrition_web_evidence_enabled
        and get_provider_secret_store().get(APIFY_API_TOKEN_SECRET) is not None
    )


def _request_json(url: str, *, data: bytes) -> object:
    request = Request(
        url,
        data=data,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "NutriFlowAI/0.1 nutrition-evidence",
        },
        method="POST",
    )
    try:
        with urlopen(
            request,
            timeout=settings.nutrition_web_evidence_timeout_seconds,
        ) as response:
            return json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RecipeEvidenceSearchError(
            "Nutrition evidence search provider is unavailable."
        ) from exc


def _normalized_text(value: str) -> str:
    return " ".join(value.casefold().replace("\xa0", " ").split())


def _basis_for_context(context: str) -> str:
    normalized = _normalized_text(context)
    compact = normalized.replace(" ", "")
    if (
        "100 g" in normalized
        or "100g" in compact
        or "por 100" in normalized
        or "/100 g" in normalized
        or "/100g" in compact
    ):
        return "per_100g"
    serving_markers = (
        "por dose",
        "por porção",
        "por porcao",
        "por pessoa",
        "por serving",
        "per serving",
        "kcal/dose",
        "kcal / dose",
        "kcal por dose",
    )
    if any(marker in normalized for marker in serving_markers):
        return "per_serving"
    return "unknown"


def extract_calorie_mentions(text: str) -> tuple[CalorieMention, ...]:
    mentions: list[CalorieMention] = []
    for match in _KCAL_PATTERN.finditer(text):
        raw_value = match.group(1).replace(",", ".")
        try:
            energy = Decimal(raw_value)
        except InvalidOperation:
            continue
        if energy <= 0 or energy > Decimal(5000):
            continue
        start = max(0, match.start() - 90)
        end = min(len(text), match.end() + 90)
        context = " ".join(text[start:end].split())
        mentions.append(
            CalorieMention(
                energy_kcal=energy,
                basis=_basis_for_context(context),
                context=context,
            )
        )
    return tuple(mentions)


def _optional_position(value: object) -> int | None:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _parse_hit(raw: object) -> RecipeEvidenceSearchHit | None:
    if not isinstance(raw, dict):
        return None
    title = str(raw.get("title") or "").strip()
    url = str(raw.get("url") or raw.get("link") or "").strip()
    if not title or not url.startswith(("http://", "https://")):
        return None
    description = str(
        raw.get("description") or raw.get("snippet") or ""
    ).strip() or None
    searchable = " ".join(value for value in (title, description) if value)
    return RecipeEvidenceSearchHit(
        title=title,
        url=url,
        description=description,
        position=_optional_position(raw.get("position")),
        calorie_mentions=extract_calorie_mentions(searchable),
    )


def _organic_results(payload: object) -> list[object]:
    if not isinstance(payload, list):
        raise RecipeEvidenceSearchError(
            "Nutrition evidence search provider returned invalid data."
        )
    results: list[object] = []
    for row in payload:
        if not isinstance(row, dict):
            continue
        if row.get("type") == "organic":
            results.append(row)
            continue
        nested = row.get("organicResults")
        if isinstance(nested, list):
            results.extend(nested)
    return results


def search_recipe_nutrition_evidence(
    recipe_name: str,
    *,
    max_results: int | None = None,
) -> RecipeEvidenceSearchResult:
    normalized_name = " ".join(recipe_name.strip().split())
    if not normalized_name:
        raise RecipeEvidenceSearchError("Recipe evidence search requires a recipe name.")
    if not settings.nutrition_web_evidence_enabled:
        raise RecipeEvidenceSearchError("Nutrition web evidence search is disabled.")

    token = get_provider_secret_store().get(APIFY_API_TOKEN_SECRET)
    if token is None:
        raise RecipeEvidenceSearchError(
            "Nutrition web evidence search requires NUTRIFLOW_APIFY_API_TOKEN."
        )

    limit = min(
        max(max_results or settings.nutrition_web_evidence_max_results, 1),
        20,
    )
    query = f'"{normalized_name}" calorias kcal receita'
    payload = json.dumps(
        {
            "queries": query,
            "maxPagesPerQuery": 1,
            "resultsPerPage": limit,
            "countryCode": "pt",
            "languageCode": "pt",
            "includeUnfilteredResults": False,
            "saveHtml": False,
            "saveHtmlToKeyValueStore": False,
        }
    ).encode("utf-8")
    separator = "&" if "?" in settings.nutrition_apify_google_search_url else "?"
    url = (
        f"{settings.nutrition_apify_google_search_url}"
        f"{separator}token={quote(token, safe='')}"
    )
    raw_results = _organic_results(_request_json(url, data=payload))

    hits: list[RecipeEvidenceSearchHit] = []
    seen_urls: set[str] = set()
    for raw in raw_results:
        hit = _parse_hit(raw)
        if hit is None or hit.url in seen_urls:
            continue
        seen_urls.add(hit.url)
        hits.append(hit)
        if len(hits) >= limit:
            break

    return RecipeEvidenceSearchResult(
        recipe_name=normalized_name,
        query=query,
        hits=tuple(hits),
    )
