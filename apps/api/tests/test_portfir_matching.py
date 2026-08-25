from decimal import Decimal

from app.services.portfir import PortfirFoodNutrition
from app.services.portfir_matching import (
    automatic_portfir_match,
    normalize_food_name,
    rank_portfir_matches,
)


def _food(code: str, name: str) -> PortfirFoodNutrition:
    return PortfirFoodNutrition(
        code=code,
        name=name,
        energy_kcal=Decimal(100),
        nutrients=(),
    )


def test_normalization_handles_accents_plural_and_low_risk_descriptors() -> None:
    assert normalize_food_name("Cebolas") == "cebola"
    ranked = rank_portfir_matches(
        "Cebola picada congelada",
        (_food("1", "Cebola, crua"), _food("2", "Cebolinho, cru")),
    )

    assert ranked[0].food.code == "1"
    assert ranked[0].score == Decimal("0.990")
    assert ranked[0].reason == "exact_core_name"


def test_automatic_match_accepts_unique_exact_core_match() -> None:
    match = automatic_portfir_match(
        "Alho congelado",
        (_food("1", "Alho, cru"), _food("2", "Alho francês, cru")),
    )

    assert match is not None
    assert match.food.code == "1"
    assert match.score == Decimal("0.990")


def test_automatic_match_rejects_ambiguous_equal_matches() -> None:
    match = automatic_portfir_match(
        "Azeite",
        (_food("1", "Azeite"), _food("2", "Azeite")),
    )

    assert match is None


def test_automatic_match_does_not_ignore_material_cooking_state() -> None:
    ranked = rank_portfir_matches(
        "Frango cozido",
        (_food("1", "Frango, cru"), _food("2", "Frango, assado")),
    )

    assert ranked[0].score < Decimal("0.985")
