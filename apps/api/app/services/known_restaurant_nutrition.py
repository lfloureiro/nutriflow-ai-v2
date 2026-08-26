import re
import unicodedata
from dataclasses import dataclass
from decimal import Decimal

from app.schemas.external_menu import ExternalMenuNutrientWrite, ExternalMenuNutritionWrite
from app.services.restaurant_menu_scraper import ScrapedMenuItem

TOMATINO_NUTRITION_SOURCE = "https://tomatino.pt/ementa/"
TOMATINO_SIZE_ESTIMATE_VERSION = "tomatino-official-size-adjust-v1"


@dataclass(frozen=True)
class _TomatinoServing:
    energy_kcal: Decimal
    protein_g: Decimal
    fiber_g: Decimal
    salt_g: Decimal
    base_pasta_g: Decimal | None


_TOMATINO_SERVINGS = {
    "salada verdi": _TomatinoServing(
        Decimal(675), Decimal("27.8"), Decimal("6.1"), Decimal("2.3"), None
    ),
    "rustica": _TomatinoServing(
        Decimal(759), Decimal("30.4"), Decimal("6.5"), Decimal("4.4"), Decimal(200)
    ),
    "sicilia": _TomatinoServing(
        Decimal(549), Decimal("31.5"), Decimal("5.3"), Decimal("3.9"), Decimal(180)
    ),
    "al nero": _TomatinoServing(
        Decimal(616), Decimal("35.5"), Decimal("6.1"), Decimal("4.3"), Decimal(200)
    ),
    "al pesto": _TomatinoServing(
        Decimal(591), Decimal("27.7"), Decimal("6.8"), Decimal("2.3"), Decimal(200)
    ),
    "carbonara": _TomatinoServing(
        Decimal(569), Decimal("33.0"), Decimal("4.6"), Decimal("4.8"), Decimal(200)
    ),
    "gamberetti": _TomatinoServing(
        Decimal(508), Decimal("24.4"), Decimal("3.2"), Decimal("1.9"), Decimal(200)
    ),
    "alfredo di roma": _TomatinoServing(
        Decimal(672), Decimal("36.1"), Decimal("6.2"), Decimal("2.9"), Decimal(200)
    ),
    "alfredo": _TomatinoServing(
        Decimal(672), Decimal("36.1"), Decimal("6.2"), Decimal("2.9"), Decimal(200)
    ),
    "padovana": _TomatinoServing(
        Decimal(522), Decimal("27.7"), Decimal("5.0"), Decimal("2.8"), Decimal(200)
    ),
    "bologna": _TomatinoServing(
        Decimal(393), Decimal("20.4"), Decimal("4.3"), Decimal("3.4"), Decimal(200)
    ),
    "toscania": _TomatinoServing(
        Decimal(804), Decimal("35.1"), Decimal("6.1"), Decimal("2.9"), Decimal(200)
    ),
    "sardegna": _TomatinoServing(
        Decimal(633), Decimal("25.2"), Decimal("6.9"), Decimal("3.1"), Decimal(200)
    ),
    "campania": _TomatinoServing(
        Decimal(432), Decimal("13.9"), Decimal("6.2"), Decimal("4.2"), Decimal(200)
    ),
    "piemonte": _TomatinoServing(
        Decimal(711), Decimal("22.5"), Decimal("4.8"), Decimal("3.5"), Decimal(200)
    ),
}

_EXTRA_PASTA_ENERGY_PER_100G = Decimal(150)
_EXTRA_PASTA_PROTEIN_PER_100G = Decimal(5)
_EXTRA_PASTA_FIBER_PER_100G = Decimal("1.8")
_EXTRA_PASTA_SODIUM_MG_PER_100G = Decimal(5)


def _normalize(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.casefold())
    ascii_text = "".join(
        character for character in normalized if not unicodedata.combining(character)
    )
    return " ".join(re.findall(r"[a-z0-9]+", ascii_text))


def _item_size_g(name: str) -> Decimal | None:
    match = re.search(r"(?<!\d)(\d{2,4})\s*g\b", name.casefold())
    return None if match is None else Decimal(match.group(1))


def _tomatino_dish_key(name: str) -> str | None:
    normalized = _normalize(name)
    without_size = re.sub(r"\b\d{2,4}g\b", "", normalized)
    without_size = " ".join(without_size.split())
    if without_size == "verdi":
        without_size = "salada verdi"
    return without_size if without_size in _TOMATINO_SERVINGS else None


def _sodium_mg_from_salt_g(salt_g: Decimal) -> Decimal:
    return (salt_g * Decimal(400)).quantize(Decimal(1))


def _nutrition(
    *,
    energy_kcal: Decimal,
    protein_g: Decimal,
    fiber_g: Decimal,
    sodium_mg: Decimal,
    evidence_level: str,
    confidence: Decimal | None,
    basis_reference: str,
) -> ExternalMenuNutritionWrite:
    return ExternalMenuNutritionWrite(
        evidence_level=evidence_level,
        confidence=confidence,
        basis_reference=basis_reference,
        reference_quantity=Decimal(1),
        reference_unit="serving",
        energy_kcal=energy_kcal,
        nutrients=[
            ExternalMenuNutrientWrite(key="protein", value=protein_g, unit="g"),
            ExternalMenuNutrientWrite(key="fiber", value=fiber_g, unit="g"),
            ExternalMenuNutrientWrite(key="sodium", value=sodium_mg, unit="mg"),
        ],
    )


def estimate_known_restaurant_nutrition(
    *,
    merchant_name: str | None,
    item: ScrapedMenuItem,
) -> ExternalMenuNutritionWrite | None:
    if merchant_name is None or "tomatino" not in _normalize(merchant_name):
        return None

    dish_key = _tomatino_dish_key(item.name)
    if dish_key is None:
        return None
    serving = _TOMATINO_SERVINGS[dish_key]
    size_g = _item_size_g(item.name)
    sodium_mg = _sodium_mg_from_salt_g(serving.salt_g)

    if serving.base_pasta_g is None or size_g is None or size_g == serving.base_pasta_g:
        return _nutrition(
            energy_kcal=serving.energy_kcal,
            protein_g=serving.protein_g,
            fiber_g=serving.fiber_g,
            sodium_mg=sodium_mg,
            evidence_level="official",
            confidence=None,
            basis_reference=TOMATINO_NUTRITION_SOURCE,
        )

    extra_pasta_g = max(size_g - serving.base_pasta_g, Decimal(0))
    extra_factor = extra_pasta_g / Decimal(100)
    return _nutrition(
        energy_kcal=(
            serving.energy_kcal + extra_factor * _EXTRA_PASTA_ENERGY_PER_100G
        ).quantize(Decimal(1)),
        protein_g=(
            serving.protein_g + extra_factor * _EXTRA_PASTA_PROTEIN_PER_100G
        ).quantize(Decimal("0.1")),
        fiber_g=(
            serving.fiber_g + extra_factor * _EXTRA_PASTA_FIBER_PER_100G
        ).quantize(Decimal("0.1")),
        sodium_mg=(
            sodium_mg + extra_factor * _EXTRA_PASTA_SODIUM_MG_PER_100G
        ).quantize(Decimal(1)),
        evidence_level="estimated",
        confidence=Decimal("0.88"),
        basis_reference=(
            f"{TOMATINO_SIZE_ESTIMATE_VERSION}:{TOMATINO_NUTRITION_SOURCE}"
        ),
    )
