import re
import unicodedata
from dataclasses import dataclass
from decimal import Decimal

from app.schemas.external_menu import ExternalMenuNutrientWrite, ExternalMenuNutritionWrite
from app.services.restaurant_menu_scraper import ScrapedMenuItem

KFC_NUTRITION_SOURCE = "https://www.vivabem.pt/tabelas/tabela_kfc.pdf"


@dataclass(frozen=True)
class _KfcServing:
    energy_kcal: Decimal
    protein_g: Decimal
    salt_g: Decimal


_HOT_WING = _KfcServing(Decimal(66), Decimal("6.8"), Decimal("0.9"))
_TENDER = _KfcServing(Decimal(76), Decimal("8.2"), Decimal("0.7"))

_KFC_SERVINGS = {
    "double krunch bbq": _KfcServing(Decimal(440), Decimal("30.1"), Decimal("4.8")),
    "o cheddar single": _KfcServing(Decimal(579), Decimal("42.2"), Decimal("4.3")),
    # The July 2026 KFC Portugal nutrition table calls the current Golden burgers
    # "Burger Glaceado Original Single/Double". Uber Eats markets the same products
    # as Golden Single/Double.
    "golden single": _KfcServing(Decimal(584), Decimal("32.1"), Decimal("4.1")),
    "golden double": _KfcServing(Decimal(804), Decimal("54.3"), Decimal("6.1")),
}


def _normalize(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.casefold())
    ascii_text = "".join(
        character for character in normalized if not unicodedata.combining(character)
    )
    return " ".join(re.findall(r"[a-z0-9]+", ascii_text))


def _quantity(normalized_name: str, product: str) -> int | None:
    if product == "hot-wings":
        match = re.search(r"\b(\d{1,2})\s+hot\s*wings?\b", normalized_name)
    else:
        match = re.search(r"\b(\d{1,2})\s+tenders\b", normalized_name)
    if match is None:
        return None
    return int(match.group(1))


def _scaled(serving: _KfcServing, quantity: int) -> ExternalMenuNutritionWrite:
    factor = Decimal(quantity)
    return ExternalMenuNutritionWrite(
        evidence_level="official",
        confidence=None,
        basis_reference=KFC_NUTRITION_SOURCE,
        reference_quantity=Decimal(1),
        reference_unit="serving",
        energy_kcal=serving.energy_kcal * factor,
        nutrients=[
            ExternalMenuNutrientWrite(
                key="protein",
                value=serving.protein_g * factor,
                unit="g",
            ),
            ExternalMenuNutrientWrite(
                key="sodium",
                value=serving.salt_g * factor * Decimal(400),
                unit="mg",
            ),
        ],
    )


def estimate_kfc_nutrition(
    *,
    merchant_name: str | None,
    item: ScrapedMenuItem,
) -> ExternalMenuNutritionWrite | None:
    if merchant_name is None or "kfc" not in _normalize(merchant_name):
        return None

    normalized_name = _normalize(item.name)

    hot_wings = _quantity(normalized_name, "hot-wings")
    if hot_wings is not None:
        return _scaled(_HOT_WING, hot_wings)

    tenders = _quantity(normalized_name, "tenders")
    if tenders is not None:
        return _scaled(_TENDER, tenders)

    serving = _KFC_SERVINGS.get(normalized_name)
    if serving is None:
        return None
    return _scaled(serving, 1)
