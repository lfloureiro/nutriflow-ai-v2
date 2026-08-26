import re
import unicodedata
from dataclasses import dataclass
from decimal import Decimal

from app.schemas.external_menu import ExternalMenuNutrientWrite, ExternalMenuNutritionWrite
from app.services.restaurant_menu_scraper import ScrapedMenuItem

BURGER_KING_NUTRITION_SOURCE = (
    "https://bk-emea-prd.s3.amazonaws.com/sites/burgerking.pt/files/documents/"
    "Nutrition_Portugal.pdf"
)


@dataclass(frozen=True)
class _BurgerKingServing:
    energy_kcal: Decimal
    protein_g: Decimal
    salt_g: Decimal


# Burger King Portugal nutrition table, current production document.
_BURGER_KING_SERVINGS = {
    "steakhouse": _BurgerKingServing(
        energy_kcal=Decimal("890.5"),
        protein_g=Decimal("48.7"),
        salt_g=Decimal("6.1"),
    ),
}


def _normalize(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.casefold())
    ascii_text = "".join(
        character for character in normalized if not unicodedata.combining(character)
    )
    return " ".join(re.findall(r"[a-z0-9]+", ascii_text))


def estimate_burgerking_nutrition(
    *,
    merchant_name: str | None,
    item: ScrapedMenuItem,
) -> ExternalMenuNutritionWrite | None:
    if merchant_name is None or "burger king" not in _normalize(merchant_name):
        return None

    serving = _BURGER_KING_SERVINGS.get(_normalize(item.name))
    if serving is None:
        return None

    return ExternalMenuNutritionWrite(
        evidence_level="official",
        confidence=None,
        basis_reference=BURGER_KING_NUTRITION_SOURCE,
        reference_quantity=Decimal(1),
        reference_unit="serving",
        energy_kcal=serving.energy_kcal,
        nutrients=[
            ExternalMenuNutrientWrite(
                key="protein",
                value=serving.protein_g,
                unit="g",
            ),
            ExternalMenuNutrientWrite(
                key="sodium",
                value=serving.salt_g * Decimal(400),
                unit="mg",
            ),
        ],
    )
