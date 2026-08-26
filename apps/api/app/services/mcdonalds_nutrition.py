import re
import unicodedata
from dataclasses import dataclass
from decimal import Decimal

from app.schemas.external_menu import ExternalMenuNutrientWrite, ExternalMenuNutritionWrite
from app.services.restaurant_menu_scraper import ScrapedMenuItem

MCDONALDS_NUTRITION_SOURCE = (
    "https://www.mcdonalds.pt/produtos/informacao-nutricional-alergenios"
)


@dataclass(frozen=True)
class _McDonaldsServing:
    energy_kcal: Decimal
    protein_g: Decimal
    fiber_g: Decimal | None
    salt_g: Decimal
    source_reference: str


def _product_source(slug: str) -> str:
    return f"https://www.mcdonalds.pt/produtos/mcmenu/sanduiches/{slug}"


_MCDONALDS_SERVINGS = {
    "big mac": _McDonaldsServing(
        Decimal(544), Decimal(27), Decimal("4.0"), Decimal("2.3"), _product_source("big-mac")
    ),
    "mcroyal bacon": _McDonaldsServing(
        Decimal(583), Decimal(33), None, Decimal("2.3"), _product_source("mcroyal-bacon")
    ),
    "cbo": _McDonaldsServing(
        Decimal(772), Decimal(30), Decimal("4.4"), Decimal("3.6"), _product_source("cbo")
    ),
    "double cheeseburger": _McDonaldsServing(
        Decimal(445),
        Decimal(28),
        Decimal("2.2"),
        Decimal("2.2"),
        _product_source("double-cheeseburger"),
    ),
    "big tasty single": _McDonaldsServing(
        Decimal(638),
        Decimal(34),
        Decimal("3.2"),
        Decimal("2.5"),
        _product_source("big-tasty-single"),
    ),
    "big arch": _McDonaldsServing(
        Decimal(1065), Decimal(57), Decimal("3.9"), Decimal("3.7"), _product_source("big-arch")
    ),
    "mcchicken": _McDonaldsServing(
        Decimal(419), Decimal(19), Decimal("3.6"), Decimal("2.1"), _product_source("mcchicken")
    ),
    "big tasty double": _McDonaldsServing(
        Decimal(957),
        Decimal(57),
        Decimal("3.2"),
        Decimal("3.5"),
        _product_source("big-tasty-double"),
    ),
    "mcroyal deluxe": _McDonaldsServing(
        Decimal(559),
        Decimal(30),
        Decimal("3.4"),
        Decimal("1.9"),
        _product_source("mcroyal-deluxe"),
    ),
    "mcroyal cheese": _McDonaldsServing(
        Decimal(547),
        Decimal(33),
        Decimal("3.0"),
        Decimal("2.6"),
        _product_source("mcroyal-cheese"),
    ),
    "chicken bacon": _McDonaldsServing(
        Decimal(413),
        Decimal(20),
        None,
        Decimal("2.2"),
        "https://www.mcdonalds.pt/produtos/europoupanca/chicken-bacon",
    ),
    "cheeseburger": _McDonaldsServing(
        Decimal(306),
        Decimal(16),
        Decimal("2.3"),
        Decimal("1.6"),
        "https://www.mcdonalds.pt/produtos/europoupanca/cheeseburger",
    ),
    "chicken mcnuggets 4": _McDonaldsServing(
        Decimal(175),
        Decimal(11),
        Decimal("0.6"),
        Decimal("0.8"),
        "https://www.mcdonalds.pt/produtos/happy-meal/sanduiches/4-chicken-mcnuggets",
    ),
    "10 chicken mcnuggets": _McDonaldsServing(
        Decimal(437),
        Decimal(27),
        Decimal("1.6"),
        Decimal("2.0"),
        "https://www.mcdonalds.pt/produtos/mcmenu/sanduiches/10-chicken-mcnuggets",
    ),
    "chicken wings 3": _McDonaldsServing(
        Decimal(219), Decimal(22), Decimal(0), Decimal("2.3"), MCDONALDS_NUTRITION_SOURCE
    ),
    "chicken wings 6": _McDonaldsServing(
        Decimal(438), Decimal(44), Decimal(0), Decimal("4.6"), MCDONALDS_NUTRITION_SOURCE
    ),
    "mccrispy bbq bacon": _McDonaldsServing(
        Decimal(675),
        Decimal(34),
        Decimal("3.9"),
        Decimal("3.0"),
        _product_source("mccrispy-bbq-bacon"),
    ),
    "mccrispy teriyaki": _McDonaldsServing(
        Decimal(630),
        Decimal(26),
        None,
        Decimal("2.9"),
        _product_source("mccrispy-teriyaki"),
    ),
    "philly cheese stack single": _McDonaldsServing(
        Decimal(575),
        Decimal(29),
        None,
        Decimal("2.0"),
        _product_source("mcphilly-cheese-stack-single"),
    ),
    "philly cheese stack double": _McDonaldsServing(
        Decimal(832),
        Decimal(48),
        None,
        Decimal("2.5"),
        _product_source("mcphilly-cheese-stack-double"),
    ),
    "garlic pepper mcnuggets 4": _McDonaldsServing(
        Decimal(178),
        Decimal(10),
        None,
        Decimal("1.1"),
        _product_source("4-garlic-pepper-mcnuggets"),
    ),
    "garlic pepper mcnuggets 10": _McDonaldsServing(
        Decimal(445),
        Decimal(25),
        None,
        Decimal("2.7"),
        _product_source("10-garlic-pepper-mcnuggets"),
    ),
}

_ALIASES = {
    "4 chicken mcnuggets": "chicken mcnuggets 4",
    "10 mcnuggets": "10 chicken mcnuggets",
    "4 garlic pepper mcnuggets": "garlic pepper mcnuggets 4",
    "10 garlic pepper mcnuggets": "garlic pepper mcnuggets 10",
}


def _normalize(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.casefold())
    ascii_text = "".join(
        character for character in normalized if not unicodedata.combining(character)
    )
    return " ".join(re.findall(r"[a-z0-9]+", ascii_text))


def _dish_key(name: str) -> str | None:
    normalized = _normalize(name)
    canonical = _ALIASES.get(normalized, normalized)
    return canonical if canonical in _MCDONALDS_SERVINGS else None


def estimate_mcdonalds_nutrition(
    *,
    merchant_name: str | None,
    item: ScrapedMenuItem,
) -> ExternalMenuNutritionWrite | None:
    if merchant_name is None or "mcdonald" not in _normalize(merchant_name):
        return None

    dish_key = _dish_key(item.name)
    if dish_key is None:
        return None
    serving = _MCDONALDS_SERVINGS[dish_key]

    nutrients = [
        ExternalMenuNutrientWrite(key="protein", value=serving.protein_g, unit="g"),
        ExternalMenuNutrientWrite(
            key="sodium",
            value=serving.salt_g * Decimal(400),
            unit="mg",
        ),
    ]
    if serving.fiber_g is not None:
        nutrients.insert(
            1,
            ExternalMenuNutrientWrite(key="fiber", value=serving.fiber_g, unit="g"),
        )

    return ExternalMenuNutritionWrite(
        evidence_level="official",
        confidence=None,
        basis_reference=serving.source_reference,
        reference_quantity=Decimal(1),
        reference_unit="serving",
        energy_kcal=serving.energy_kcal,
        nutrients=nutrients,
    )
