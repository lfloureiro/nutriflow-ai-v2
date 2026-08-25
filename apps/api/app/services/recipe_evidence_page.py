import json
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

from app.core.config import settings
from app.services.nutrition_learning import RecipeEvidence

_CALORIE_PATTERN = re.compile(r"(?<!\d)(\d{1,5}(?:[.,]\d+)?)\s*kcal\b", re.IGNORECASE)
_SERVING_PATTERN = re.compile(
    r"(?<!\d)(\d+(?:[.,]\d+)?)\s*(?:porcoes?|porções|pessoas?|servings?|doses?)\b",
    re.IGNORECASE,
)
_LEADING_QUANTITY = re.compile(
    r"^\s*(?:\d+(?:[.,]\d+)?|[¼½¾⅓⅔⅛⅜⅝⅞])(?:\s*[-–]\s*\d+(?:[.,]\d+)?)?\s*",
    re.IGNORECASE,
)
_LEADING_MEASURE = re.compile(
    r"^(?:"
    r"kg|g|mg|l|cl|ml|"
    r"colheres?\s+de\s+sopa|colheres?\s+de\s+chá|colheres?|"
    r"c\.?\s*de\s+sopa|c\.?\s*de\s+chá|"
    r"chávenas?|xícaras?|cups?|tablespoons?|tbsp|teaspoons?|tsp|"
    r"dentes?|latas?|embalagens?|pacotes?|unidades?"
    r")\b\s*(?:de\s+)?",
    re.IGNORECASE,
)


class RecipeEvidencePageError(ValueError):
    pass


@dataclass(frozen=True)
class StructuredRecipePage:
    source_reference: str
    recipe_name: str
    energy_kcal_per_serving: Decimal | None
    serving_count: Decimal | None
    ingredient_names: tuple[str, ...]

    def as_recipe_evidence(self, *, source_quality: Decimal = Decimal("0.80")) -> RecipeEvidence | None:
        if self.energy_kcal_per_serving is None:
            return None
        host = urlparse(self.source_reference).hostname or "web"
        return RecipeEvidence(
            source=host.casefold().removeprefix("www."),
            source_reference=self.source_reference,
            recipe_name=self.recipe_name,
            energy_kcal_per_serving=self.energy_kcal_per_serving,
            serving_count=self.serving_count,
            ingredient_names=self.ingredient_names,
            source_quality=source_quality,
        )


def _request_html(url: str) -> str:
    request = Request(
        url,
        headers={
            "Accept": "text/html,application/xhtml+xml",
            "User-Agent": "NutriFlowAI/0.1 nutrition-evidence",
        },
    )
    try:
        with urlopen(
            request,
            timeout=min(settings.nutrition_web_evidence_timeout_seconds, 20.0),
        ) as response:
            content_type = response.headers.get_content_charset() or "utf-8"
            return response.read().decode(content_type, errors="replace")
    except (HTTPError, URLError, TimeoutError, UnicodeError) as exc:
        raise RecipeEvidencePageError("Recipe evidence page is unavailable.") from exc


def _recipe_nodes(value: object) -> list[dict[str, object]]:
    nodes: list[dict[str, object]] = []
    if isinstance(value, list):
        for item in value:
            nodes.extend(_recipe_nodes(item))
        return nodes
    if not isinstance(value, dict):
        return nodes

    graph = value.get("@graph")
    if isinstance(graph, list):
        nodes.extend(_recipe_nodes(graph))

    raw_type = value.get("@type")
    types = [raw_type] if isinstance(raw_type, str) else raw_type
    if isinstance(types, list) and any(
        isinstance(item, str) and item.casefold() == "recipe" for item in types
    ):
        nodes.append(value)
    return nodes


def _decimal_from_calories(value: object) -> Decimal | None:
    if isinstance(value, (int, float, Decimal)) and not isinstance(value, bool):
        parsed = Decimal(str(value))
        return parsed if parsed > 0 else None
    if not isinstance(value, str):
        return None
    match = _CALORIE_PATTERN.search(value)
    raw = match.group(1) if match else value.strip()
    try:
        parsed = Decimal(raw.replace(",", "."))
    except (InvalidOperation, ValueError):
        return None
    return parsed if 0 < parsed <= Decimal(5000) else None


def _energy(node: dict[str, object]) -> Decimal | None:
    nutrition = node.get("nutrition")
    if isinstance(nutrition, dict):
        calories = _decimal_from_calories(nutrition.get("calories"))
        if calories is not None:
            return calories
    return None


def _serving_count(value: object) -> Decimal | None:
    if isinstance(value, (int, float, Decimal)) and not isinstance(value, bool):
        parsed = Decimal(str(value))
        return parsed if parsed > 0 else None
    values = value if isinstance(value, list) else [value]
    for item in values:
        if not isinstance(item, str):
            continue
        match = _SERVING_PATTERN.search(item)
        if match is None:
            stripped = item.strip().replace(",", ".")
            try:
                parsed = Decimal(stripped)
            except InvalidOperation:
                continue
        else:
            parsed = Decimal(match.group(1).replace(",", "."))
        if parsed > 0:
            return parsed
    return None


def ingredient_name_from_line(value: str) -> str:
    cleaned = " ".join(value.replace("\xa0", " ").split()).strip(" -–,;:")
    cleaned = _LEADING_QUANTITY.sub("", cleaned, count=1).strip(" -–,;:")
    cleaned = _LEADING_MEASURE.sub("", cleaned, count=1).strip(" -–,;:")
    return cleaned or " ".join(value.split())


def _ingredient_names(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    result: list[str] = []
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, str) or not item.strip():
            continue
        name = ingredient_name_from_line(item)
        key = name.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(name)
    return tuple(result)


def parse_structured_recipe_pages(html: str, *, source_reference: str) -> tuple[StructuredRecipePage, ...]:
    soup = BeautifulSoup(html, "html.parser")
    result: list[StructuredRecipePage] = []
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw = script.string or script.get_text()
        if not raw.strip():
            continue
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            continue
        for node in _recipe_nodes(payload):
            name = str(node.get("name") or "").strip()
            if not name:
                continue
            result.append(
                StructuredRecipePage(
                    source_reference=source_reference,
                    recipe_name=name,
                    energy_kcal_per_serving=_energy(node),
                    serving_count=_serving_count(node.get("recipeYield")),
                    ingredient_names=_ingredient_names(node.get("recipeIngredient")),
                )
            )
    return tuple(result)


def fetch_structured_recipe_pages(url: str) -> tuple[StructuredRecipePage, ...]:
    return parse_structured_recipe_pages(_request_html(url), source_reference=url)
