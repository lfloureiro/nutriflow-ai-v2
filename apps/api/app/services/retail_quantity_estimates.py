import re
import unicodedata
from dataclasses import dataclass
from decimal import Decimal

PACKAGE_UNITS = frozenset({"emb", "emb.", "embalagem", "pacote", "pack"})
_DEFAULT_SERVING_COUNT = Decimal(4)
_DEFAULT_QUANTITY_PER_SERVING = Decimal(100)


@dataclass(frozen=True)
class RetailQuantityEstimate:
    reference_unit: str
    quantity_in_reference_unit: Decimal
    source: str
    source_reference: str | None
    description: str
    confidence: str


@dataclass(frozen=True)
class RetailPackageReference:
    mass_g: Decimal | None
    volume_ml: Decimal | None
    source_reference: str
    description: str


def _normalized(value: str) -> str:
    text = unicodedata.normalize("NFKD", value.casefold())
    text = "".join(
        character for character in text if not unicodedata.combining(character)
    )
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


_REFERENCES = {
    "natas": RetailPackageReference(
        mass_g=Decimal(200),
        volume_ml=Decimal(200),
        source_reference="https://www.continente.pt/laticinios-e-ovos/natas-e-bechamel/",
        description="Typical Continente cooking-cream package: 200 ml.",
    ),
    "massa quebrada": RetailPackageReference(
        mass_g=Decimal(230),
        volume_ml=None,
        source_reference=(
            "https://www.continente.pt/produto/"
            "massa-quebrada-continente-continente-4297266.html"
        ),
        description="Continente shortcrust pastry package: 230 g.",
    ),
    "queijo ralado": RetailPackageReference(
        mass_g=Decimal(200),
        volume_ml=None,
        source_reference=(
            "https://www.continente.pt/produto/"
            "queijo-ralado-para-massas-continente-continente-7619407.html"
        ),
        description="Typical Continente grated-cheese package: 200 g.",
    ),
    "feta": RetailPackageReference(
        mass_g=Decimal(150),
        volume_ml=None,
        source_reference="https://www.continente.pt/frescos/queijos/queijos-do-mundo/continente-2/",
        description="Continente feta package reference: 150 g.",
    ),
    "cogumelos": RetailPackageReference(
        mass_g=Decimal(300),
        volume_ml=None,
        source_reference=(
            "https://www.continente.pt/frescos/legumes/"
            "cogumelos-espargos-e-exoticos/continente-2/"
        ),
        description="Typical Continente fresh-mushroom package: 300 g.",
    ),
    "espinafres": RetailPackageReference(
        mass_g=Decimal(400),
        volume_ml=None,
        source_reference="https://www.continente.pt/congelados/frutas-e-legumes/",
        description="Typical supermarket frozen-spinach package reference: 400 g.",
    ),
}


def _reference_for_name(ingredient_name: str) -> RetailPackageReference | None:
    normalized = _normalized(ingredient_name)
    direct = _REFERENCES.get(normalized)
    if direct is not None:
        return direct
    for key, reference in _REFERENCES.items():
        if key in normalized:
            return reference
    return None


def _serving_count(value: Decimal | None) -> Decimal:
    if value is None or value <= 0:
        return _DEFAULT_SERVING_COUNT
    return value


def estimate_retail_package_quantity(
    *,
    ingredient_name: str,
    composition_reference_unit: str,
    serving_count: Decimal | None,
) -> RetailQuantityEstimate | None:
    unit = composition_reference_unit.strip().casefold()
    mass_reference = unit in {"g", "kg"}
    volume_reference = unit in {"ml", "cl", "l"}
    if not mass_reference and not volume_reference:
        return None

    known = _reference_for_name(ingredient_name)
    if known is not None:
        quantity = known.mass_g if mass_reference else known.volume_ml
        if quantity is not None:
            return RetailQuantityEstimate(
                reference_unit="g" if mass_reference else "ml",
                quantity_in_reference_unit=quantity,
                source="retail-reference",
                source_reference=known.source_reference,
                description=known.description,
                confidence="medium",
            )

    servings = _serving_count(serving_count)
    quantity = servings * _DEFAULT_QUANTITY_PER_SERVING
    reference_unit = "g" if mass_reference else "ml"
    return RetailQuantityEstimate(
        reference_unit=reference_unit,
        quantity_in_reference_unit=quantity,
        source="retail-heuristic",
        source_reference=None,
        description=(
            "Estimated supermarket package for the recipe: "
            f"{_DEFAULT_QUANTITY_PER_SERVING} {reference_unit} per serving "
            f"x {servings} servings."
        ),
        confidence="low",
    )
