import re
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher
from decimal import Decimal

from app.services.portfir import PortfirFoodNutrition

AUTO_MATCH_MIN_SCORE = Decimal("0.985")
AUTO_MATCH_MIN_MARGIN = Decimal("0.030")

_LOW_RISK_DESCRIPTORS = frozenset(
    {
        "cru",
        "crua",
        "crus",
        "cruas",
        "fresco",
        "fresca",
        "frescos",
        "frescas",
        "congelado",
        "congelada",
        "congelados",
        "congeladas",
        "picado",
        "picada",
        "picados",
        "picadas",
        "lavado",
        "lavada",
        "lavados",
        "lavadas",
        "embalado",
        "embalada",
        "embalados",
        "embaladas",
    }
)
_SINGULAR_FORMS = {
    "azeitonas": "azeitona",
    "batatas": "batata",
    "cebolas": "cebola",
    "cebolinhas": "cebolinha",
    "cenouras": "cenoura",
    "cogumelos": "cogumelo",
    "ervilhas": "ervilha",
    "ovos": "ovo",
    "tomates": "tomate",
}


@dataclass(frozen=True)
class PortfirMatch:
    food: PortfirFoodNutrition
    score: Decimal
    normalized_query: str
    normalized_candidate: str
    reason: str


def normalize_food_name(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.casefold())
    ascii_text = "".join(
        character for character in normalized if not unicodedata.combining(character)
    )
    tokens = re.findall(r"[a-z0-9]+", ascii_text)
    tokens = [_SINGULAR_FORMS.get(token, token) for token in tokens]
    return " ".join(tokens)


def _core_name(value: str) -> str:
    tokens = normalize_food_name(value).split()
    return " ".join(token for token in tokens if token not in _LOW_RISK_DESCRIPTORS)


def _score(query: str, candidate: str) -> tuple[Decimal, str]:
    normalized_query = normalize_food_name(query)
    normalized_candidate = normalize_food_name(candidate)
    if normalized_query == normalized_candidate:
        return Decimal(1), "exact_name"

    query_core = _core_name(query)
    candidate_core = _core_name(candidate)
    if query_core and query_core == candidate_core:
        return Decimal("0.990"), "exact_core_name"

    query_tokens = set(query_core.split())
    candidate_tokens = set(candidate_core.split())
    union = query_tokens | candidate_tokens
    jaccard = Decimal(0)
    if union:
        jaccard = Decimal(len(query_tokens & candidate_tokens)) / Decimal(len(union))
    sequence = Decimal(str(SequenceMatcher(None, query_core, candidate_core).ratio()))
    combined = (sequence * Decimal("0.70")) + (jaccard * Decimal("0.30"))
    return combined.quantize(Decimal("0.001")), "fuzzy"


def rank_portfir_matches(
    query: str,
    foods: tuple[PortfirFoodNutrition, ...],
    *,
    limit: int = 5,
) -> tuple[PortfirMatch, ...]:
    if not query.strip():
        return ()
    ranked = [
        PortfirMatch(
            food=food,
            score=score,
            normalized_query=normalize_food_name(query),
            normalized_candidate=normalize_food_name(food.name),
            reason=reason,
        )
        for food in foods
        for score, reason in (_score(query, food.name),)
    ]
    ranked.sort(key=lambda item: (item.score, item.food.name.casefold()), reverse=True)
    return tuple(ranked[: max(limit, 1)])


def automatic_portfir_match(
    query: str,
    foods: tuple[PortfirFoodNutrition, ...],
) -> PortfirMatch | None:
    ranked = rank_portfir_matches(query, foods, limit=2)
    if not ranked or ranked[0].score < AUTO_MATCH_MIN_SCORE:
        return None
    if len(ranked) > 1 and ranked[0].score - ranked[1].score < AUTO_MATCH_MIN_MARGIN:
        return None
    return ranked[0]
