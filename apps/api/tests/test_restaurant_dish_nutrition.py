from decimal import Decimal

from app.services.restaurant_dish_nutrition import (
    STRUCTURAL_ESTIMATE_VERSION,
    estimate_structural_restaurant_dish_nutrition,
)
from app.services.restaurant_menu_scraper import ScrapedMenuItem


def _item(name: str, description: str | None = None) -> ScrapedMenuItem:
    return ScrapedMenuItem(
        name=name,
        description=description,
        price=Decimal("10.00"),
        currency="EUR",
        energy_kcal=None,
        source_url="https://example.test/menu",
    )


def _nutrient_value(estimate, key: str) -> Decimal:
    return next(
        nutrient.value
        for nutrient in estimate.nutrition.nutrients
        if nutrient.key == key
    )


def test_structural_estimate_for_beef_oyster_sauce_and_fried_rice() -> None:
    estimate = estimate_structural_restaurant_dish_nutrition(
        _item("4. Vaca com Molho de Ostras e Arroz Chao Chao")
    )

    assert estimate is not None
    assert Decimal(550) <= estimate.nutrition.energy_kcal <= Decimal(850)
    assert _nutrient_value(estimate, "protein") >= Decimal(20)
    assert estimate.nutrition.evidence_level == "estimated"
    assert estimate.nutrition.confidence is not None
    assert estimate.nutrition.basis_reference.startswith(STRUCTURAL_ESTIMATE_VERSION)


def test_structural_estimate_for_rice_noodles_with_shrimp() -> None:
    estimate = estimate_structural_restaurant_dish_nutrition(
        _item("118. Massa de Arroz Mifan com Gambas")
    )

    assert estimate is not None
    assert Decimal(430) <= estimate.nutrition.energy_kcal <= Decimal(700)
    assert _nutrient_value(estimate, "protein") >= Decimal(20)


def test_structural_estimate_for_soup() -> None:
    estimate = estimate_structural_restaurant_dish_nutrition(
        _item("61. Sopa de Milho Doce")
    )

    assert estimate is not None
    assert Decimal(120) <= estimate.nutrition.energy_kcal <= Decimal(280)
    assert _nutrient_value(estimate, "fiber") >= Decimal(2)


def test_structural_estimate_for_carbonara() -> None:
    estimate = estimate_structural_restaurant_dish_nutrition(
        _item("Carbonara", "Massa com molho carbonara, queijo e bacon.")
    )

    assert estimate is not None
    assert Decimal(650) <= estimate.nutrition.energy_kcal <= Decimal(1000)
    assert _nutrient_value(estimate, "protein") >= Decimal(20)


def test_structural_estimate_does_not_invent_unknown_dish() -> None:
    estimate = estimate_structural_restaurant_dish_nutrition(_item("Especial da Casa 27"))

    assert estimate is None
