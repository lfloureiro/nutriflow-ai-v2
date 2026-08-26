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
BURGER_KING_NUTRITION_SOURCE_DATE = "2018-10-10"


@dataclass(frozen=True)
class _BurgerKingServing:
    energy_kcal: Decimal
    protein_g: Decimal
    fiber_g: Decimal
    sodium_mg: Decimal


# Official Burger King Portugal nutrition document. The document itself is dated
# 2018-10-10, so only exact classic-product name matches are treated as official.
# Current/promotional products that are absent from that document must fall back to
# another evidence source rather than inheriting values from a similar product.
_BURGER_KING_SERVINGS = {
    "whopper": _BurgerKingServing(
        energy_kcal=Decimal("640.3"),
        protein_g=Decimal("26.7"),
        fiber_g=Decimal("3.2"),
        sodium_mg=Decimal(929),
    ),
    "double whopper": _BurgerKingServing(
        energy_kcal=Decimal("882.5"),
        protein_g=Decimal("44.8"),
        fiber_g=Decimal("3.2"),
        sodium_mg=Decimal(986),
    ),
    "triple whopper": _BurgerKingServing(
        energy_kcal=Decimal("1124.8"),
        protein_g=Decimal("62.9"),
        fiber_g=Decimal("3.2"),
        sodium_mg=Decimal(1043),
    ),
    "steakhouse": _BurgerKingServing(
        energy_kcal=Decimal("890.5"),
        protein_g=Decimal("37.2"),
        fiber_g=Decimal("6.1"),
        sodium_mg=Decimal(1416),
    ),
    "big king": _BurgerKingServing(
        energy_kcal=Decimal("477.4"),
        protein_g=Decimal("24.5"),
        fiber_g=Decimal("2.7"),
        sodium_mg=Decimal(884),
    ),
    "burger": _BurgerKingServing(
        energy_kcal=Decimal("246.4"),
        protein_g=Decimal("12.4"),
        fiber_g=Decimal("2.0"),
        sodium_mg=Decimal(470),
    ),
    "cheeseburger": _BurgerKingServing(
        energy_kcal=Decimal("289.8"),
        protein_g=Decimal("14.7"),
        fiber_g=Decimal("2.1"),
        sodium_mg=Decimal(712),
    ),
    "crispy chicken": _BurgerKingServing(
        energy_kcal=Decimal("516.0"),
        protein_g=Decimal("16.4"),
        fiber_g=Decimal("3.3"),
        sodium_mg=Decimal(725),
    ),
    "long chicken": _BurgerKingServing(
        energy_kcal=Decimal("605.6"),
        protein_g=Decimal("25.0"),
        fiber_g=Decimal("3.9"),
        sodium_mg=Decimal(1265),
    ),
    "chicken burger": _BurgerKingServing(
        energy_kcal=Decimal("393.1"),
        protein_g=Decimal("11.0"),
        fiber_g=Decimal("2.6"),
        sodium_mg=Decimal(718),
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
                key="fiber",
                value=serving.fiber_g,
                unit="g",
            ),
            ExternalMenuNutrientWrite(
                key="sodium",
                value=serving.sodium_mg,
                unit="mg",
            ),
        ],
    )
