import re
import unicodedata
from dataclasses import dataclass
from decimal import Decimal

from app.schemas.external_menu import ExternalMenuNutrientWrite, ExternalMenuNutritionWrite
from app.services.restaurant_menu_scraper import ScrapedMenuItem

PRONTO_A_COMER_ESTIMATE_VERSION = "pronto-a-comer-carnaxide-structural-v1"


@dataclass(frozen=True)
class _ProntoServing:
    energy_kcal: Decimal
    protein_g: Decimal
    fiber_g: Decimal
    sodium_mg: Decimal
    confidence: Decimal


# Curated structural estimates for the current Pronto a Comer de Carnaxide menu.
# These are deliberately marked estimated: the merchant does not publish nutrition
# or portion weights in the marketplace listing. Exact item-name matching keeps the
# estimates from leaking into unrelated dishes or future menu variants.
_PRONTO_SERVINGS = {
    "bacalhau a bras": _ProntoServing(
        Decimal(650), Decimal(32), Decimal(4), Decimal(1200), Decimal("0.64")
    ),
    "meio frango assado": _ProntoServing(
        Decimal(650), Decimal(65), Decimal(0), Decimal(1100), Decimal("0.60")
    ),
    "caldeirada de polvo c batata doce": _ProntoServing(
        Decimal(550), Decimal(35), Decimal(5), Decimal(1000), Decimal("0.64")
    ),
    "perna de porco assada": _ProntoServing(
        Decimal(600), Decimal(45), Decimal(2), Decimal(1100), Decimal("0.60")
    ),
    "coelho assado c batatas": _ProntoServing(
        Decimal(620), Decimal(45), Decimal(5), Decimal(900), Decimal("0.64")
    ),
    "arroz de tamboril": _ProntoServing(
        Decimal(600), Decimal(35), Decimal(3), Decimal(1100), Decimal("0.62")
    ),
    "robalo grelhado c batata": _ProntoServing(
        Decimal(520), Decimal(40), Decimal(4), Decimal(700), Decimal("0.66")
    ),
    "vitela c cogumelos": _ProntoServing(
        Decimal(560), Decimal(40), Decimal(2), Decimal(900), Decimal("0.58")
    ),
    "choquinhos a algarvia": _ProntoServing(
        Decimal(520), Decimal(35), Decimal(2), Decimal(1000), Decimal("0.58")
    ),
    "costeletas de porco a salsicheiro": _ProntoServing(
        Decimal(700), Decimal(45), Decimal(2), Decimal(1500), Decimal("0.58")
    ),
}


def _normalize(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.casefold())
    ascii_text = "".join(
        character for character in normalized if not unicodedata.combining(character)
    )
    return " ".join(re.findall(r"[a-z0-9]+", ascii_text))


def estimate_pronto_a_comer_nutrition(
    *,
    merchant_name: str | None,
    item: ScrapedMenuItem,
) -> ExternalMenuNutritionWrite | None:
    if merchant_name is None or "pronto a comer de carnaxide" not in _normalize(
        merchant_name
    ):
        return None

    serving = _PRONTO_SERVINGS.get(_normalize(item.name))
    if serving is None:
        return None

    return ExternalMenuNutritionWrite(
        evidence_level="estimated",
        confidence=serving.confidence,
        basis_reference=PRONTO_A_COMER_ESTIMATE_VERSION,
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
