from decimal import Decimal

from app.services.external_dish_nutrition import is_non_meal_menu_item
from app.services.known_restaurant_nutrition import (
    TOMATINO_NUTRITION_SOURCE,
    TOMATINO_SIZE_ESTIMATE_VERSION,
    estimate_known_restaurant_nutrition,
)
from app.services.restaurant_menu_scraper import ScrapedMenuItem


def _item(name: str, description: str | None = None) -> ScrapedMenuItem:
    return ScrapedMenuItem(
        name=name,
        description=description,
        price=Decimal("10.00"),
        currency="EUR",
        energy_kcal=None,
        source_url="https://www.ubereats.com/pt/store/tomatino/example",
    )


def _nutrient_value(nutrition, key: str) -> Decimal:
    return next(
        nutrient.value
        for nutrient in nutrition.nutrients
        if nutrient.key == key
    )


def test_tomatino_standard_carbonara_uses_official_nutrition() -> None:
    nutrition = estimate_known_restaurant_nutrition(
        merchant_name="Tomatino (Amoreiras)",
        item=_item("Carbonara 200g"),
    )

    assert nutrition is not None
    assert nutrition.evidence_level == "official"
    assert nutrition.energy_kcal == Decimal(569)
    assert _nutrient_value(nutrition, "protein") == Decimal("33.0")
    assert nutrition.basis_reference == TOMATINO_NUTRITION_SOURCE


def test_tomatino_campania_uses_official_nutrition() -> None:
    nutrition = estimate_known_restaurant_nutrition(
        merchant_name="Tomatino (Strada Outlet)",
        item=_item("Campania 200g"),
    )

    assert nutrition is not None
    assert nutrition.evidence_level == "official"
    assert nutrition.energy_kcal == Decimal(432)
    assert _nutrient_value(nutrition, "fiber") == Decimal("6.2")


def test_tomatino_larger_portion_is_derived_from_official_standard() -> None:
    nutrition = estimate_known_restaurant_nutrition(
        merchant_name="Tomatino (Strada Outlet)",
        item=_item("Carbonara 325g"),
    )

    assert nutrition is not None
    assert nutrition.evidence_level == "estimated"
    assert nutrition.confidence == Decimal("0.88")
    assert nutrition.energy_kcal == Decimal(757)
    assert nutrition.basis_reference is not None
    assert nutrition.basis_reference.startswith(TOMATINO_SIZE_ESTIMATE_VERSION)


def test_known_restaurant_nutrition_does_not_apply_to_other_merchants() -> None:
    nutrition = estimate_known_restaurant_nutrition(
        merchant_name="Outro Restaurante",
        item=_item("Carbonara 200g"),
    )

    assert nutrition is None


def test_delivery_non_meal_items_are_not_candidates_for_nutrition_ranking() -> None:
    assert is_non_meal_menu_item("Limonada Ananás")
    assert is_non_meal_menu_item("Coca-Cola Zero")
    assert is_non_meal_menu_item("Molho Extra")
    assert is_non_meal_menu_item("Talheres Descartáveis")
    assert not is_non_meal_menu_item("Vaca com Molho de Ostras e Arroz Chao Chao")
