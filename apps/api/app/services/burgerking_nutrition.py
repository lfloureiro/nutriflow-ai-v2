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
BURGER_KING_WEB_REFERENCE_SOURCE = (
    "https://www.fatsecret.pt/calorias-nutri%C3%A7%C3%A3o/burger-king"
)
BURGER_KING_PRINGLES_ESTIMATE_VERSION = "burger-king-pringles-structural-v1"


@dataclass(frozen=True)
class _BurgerKingServing:
    energy_kcal: Decimal
    protein_g: Decimal
    fiber_g: Decimal
    sodium_mg: Decimal


@dataclass(frozen=True)
class _BurgerKingWebServing:
    energy_kcal: Decimal
    protein_g: Decimal
    confidence: Decimal = Decimal("0.82")


# Official Burger King Portugal nutrition document. The document itself is dated
# 2018-10-10, so only exact classic-product name matches are treated as official.
# Current/promotional products that are absent from that document must use another
# evidence source rather than inheriting values from a vaguely similar product.
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


# Exact current-menu names with secondary web nutrition evidence. These values are
# deliberately labelled estimated because the source is not Burger King Portugal.
# They are still substantially safer than allowing the generic dish estimator to
# infer values such as 50 kcal for a Whopper variant.
_BURGER_KING_WEB_SERVINGS = {
    "double cheese": _BurgerKingWebServing(Decimal(387), Decimal("23.2")),
    "double crispy chicken": _BurgerKingWebServing(Decimal(742), Decimal("27.2")),
    "chicken krispper": _BurgerKingWebServing(Decimal(800), Decimal("36.0")),
    "cbk": _BurgerKingWebServing(Decimal(787), Decimal("29.6")),
    "big king frango": _BurgerKingWebServing(
        Decimal(640), Decimal("20.0"), Decimal("0.72")
    ),
    "whopper spicy": _BurgerKingWebServing(Decimal(645), Decimal("32.4")),
    "double whopper spicy": _BurgerKingWebServing(Decimal(895), Decimal("53.8")),
    "triple whopper spicy": _BurgerKingWebServing(Decimal(1145), Decimal("75.2")),
    "spicy krispper": _BurgerKingWebServing(Decimal(712), Decimal("35.6")),
    "long chicken spicy": _BurgerKingWebServing(Decimal(540), Decimal("23.4")),
    "western xxl": _BurgerKingWebServing(Decimal(584), Decimal("30.6")),
    "double western xxl": _BurgerKingWebServing(Decimal(868), Decimal("50.9")),
    "triple western xxl": _BurgerKingWebServing(Decimal(1226), Decimal("75.4")),
}


# The current Pringles promotion has a detailed marketplace ingredient description
# but no reliable published nutrition table found for Portugal. Estimate the burger
# structurally from current/reference Burger King components instead of handing the
# item to the generic restaurant estimator. Energy assumptions per serving:
# brioche 230, sauce 140, bacon 52, cheddar 60, onion 10, Whopper patty 210,
# crispy chicken fillet 236. Protein follows the same coarse component model.
_BURGER_KING_PRINGLES_ESTIMATES = {
    "pringles sour creamy": _BurgerKingWebServing(
        Decimal(702), Decimal("35.3"), Decimal("0.60")
    ),
    "pringles sour creamy double": _BurgerKingWebServing(
        Decimal(912), Decimal("53.4"), Decimal("0.60")
    ),
    "pringles sour creamy crispy": _BurgerKingWebServing(
        Decimal(728), Decimal("28.4"), Decimal("0.58")
    ),
    "pringles sour cream double crispy": _BurgerKingWebServing(
        Decimal(964), Decimal("39.6"), Decimal("0.58")
    ),
}


def _normalize(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.casefold())
    ascii_text = "".join(
        character for character in normalized if not unicodedata.combining(character)
    )
    return " ".join(re.findall(r"[a-z0-9]+", ascii_text))


def _estimated_nutrition(
    serving: _BurgerKingWebServing,
    *,
    basis_reference: str,
) -> ExternalMenuNutritionWrite:
    return ExternalMenuNutritionWrite(
        evidence_level="estimated",
        confidence=serving.confidence,
        basis_reference=basis_reference,
        reference_quantity=Decimal(1),
        reference_unit="serving",
        energy_kcal=serving.energy_kcal,
        nutrients=[
            ExternalMenuNutrientWrite(
                key="protein",
                value=serving.protein_g,
                unit="g",
            )
        ],
    )


def estimate_burgerking_nutrition(
    *,
    merchant_name: str | None,
    item: ScrapedMenuItem,
) -> ExternalMenuNutritionWrite | None:
    if merchant_name is None or "burger king" not in _normalize(merchant_name):
        return None

    item_key = _normalize(item.name)
    serving = _BURGER_KING_SERVINGS.get(item_key)
    if serving is not None:
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

    web_serving = _BURGER_KING_WEB_SERVINGS.get(item_key)
    if web_serving is not None:
        return _estimated_nutrition(
            web_serving,
            basis_reference=BURGER_KING_WEB_REFERENCE_SOURCE,
        )

    promo_serving = _BURGER_KING_PRINGLES_ESTIMATES.get(item_key)
    if promo_serving is not None:
        return _estimated_nutrition(
            promo_serving,
            basis_reference=BURGER_KING_PRINGLES_ESTIMATE_VERSION,
        )

    return None
