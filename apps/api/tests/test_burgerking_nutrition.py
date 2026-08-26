from decimal import Decimal

from app.services.burgerking_nutrition import (
    BURGER_KING_NUTRITION_SOURCE,
    BURGER_KING_PRINGLES_ESTIMATE_VERSION,
    BURGER_KING_WEB_REFERENCE_SOURCE,
    estimate_burgerking_nutrition,
)
from app.services.external_dish_nutrition import is_non_meal_menu_item
from app.services.restaurant_menu_scraper import ScrapedMenuItem


def _item(name: str, description: str | None = None) -> ScrapedMenuItem:
    return ScrapedMenuItem(
        name=name,
        description=description,
        price=Decimal("10.00"),
        currency="EUR",
        energy_kcal=None,
        source_url="https://www.ubereats.com/pt/store/burger-king-colombo/example",
    )


def _nutrient_value(nutrition, key: str) -> Decimal:
    return next(
        nutrient.value
        for nutrient in nutrition.nutrients
        if nutrient.key == key
    )


def test_burgerking_steakhouse_uses_official_portugal_nutrition() -> None:
    nutrition = estimate_burgerking_nutrition(
        merchant_name="Burger King (Colombo)",
        item=_item("Steakhouse"),
    )

    assert nutrition is not None
    assert nutrition.evidence_level == "official"
    assert nutrition.confidence is None
    assert nutrition.energy_kcal == Decimal("890.5")
    assert _nutrient_value(nutrition, "protein") == Decimal("37.2")
    assert _nutrient_value(nutrition, "fiber") == Decimal("6.1")
    assert _nutrient_value(nutrition, "sodium") == Decimal(1416)
    assert nutrition.basis_reference == BURGER_KING_NUTRITION_SOURCE


def test_burgerking_current_classic_names_match_official_table() -> None:
    expected = {
        "Whopper®": ("640.3", "26.7", "3.2", "929"),
        "Long Chicken®": ("605.6", "25.0", "3.9", "1265"),
        "Crispy Chicken": ("516.0", "16.4", "3.3", "725"),
        "Cheeseburger": ("289.8", "14.7", "2.1", "712"),
        "Burger": ("246.4", "12.4", "2.0", "470"),
        "Chicken Burger": ("393.1", "11.0", "2.6", "718"),
    }

    for name, (energy, protein, fiber, sodium) in expected.items():
        nutrition = estimate_burgerking_nutrition(
            merchant_name="Burger King (Colombo)",
            item=_item(name),
        )
        assert nutrition is not None
        assert nutrition.energy_kcal == Decimal(energy)
        assert _nutrient_value(nutrition, "protein") == Decimal(protein)
        assert _nutrient_value(nutrition, "fiber") == Decimal(fiber)
        assert _nutrient_value(nutrition, "sodium") == Decimal(sodium)


def test_burgerking_current_web_reference_variants_are_explicit_estimates() -> None:
    expected = {
        "Double Cheese": ("387", "23.2"),
        "Double Crispy Chicken": ("742", "27.2"),
        "Chicken Krispper®": ("800", "36.0"),
        "Cbk": ("787", "29.6"),
        "Big King® Frango": ("640", "20.0"),
        "Whopper® Spicy": ("645", "32.4"),
        "Double Whopper® Spicy": ("895", "53.8"),
        "Triple Whopper® Spicy": ("1145", "75.2"),
        "Spicy Krispper®": ("712", "35.6"),
        "Long Chicken® Spicy": ("540", "23.4"),
        "Western Xxl": ("584", "30.6"),
        "Triple Western Xxl": ("1226", "75.4"),
    }

    for name, (energy, protein) in expected.items():
        nutrition = estimate_burgerking_nutrition(
            merchant_name="Burger King (Colombo)",
            item=_item(name),
        )
        assert nutrition is not None
        assert nutrition.evidence_level == "estimated"
        assert nutrition.confidence is not None
        assert nutrition.energy_kcal == Decimal(energy)
        assert _nutrient_value(nutrition, "protein") == Decimal(protein)
        assert nutrition.basis_reference == BURGER_KING_WEB_REFERENCE_SOURCE


def test_burgerking_pringles_promotion_uses_chain_specific_structural_estimate() -> None:
    expected = {
        "Pringles Sour Creamy": "702",
        "Pringles Sour Creamy Double": "912",
        "Pringles Sour Creamy Crispy": "728",
        "Pringles Sour Cream Double Crispy": "964",
    }

    for name, energy in expected.items():
        nutrition = estimate_burgerking_nutrition(
            merchant_name="Burger King (Colombo)",
            item=_item(name),
        )
        assert nutrition is not None
        assert nutrition.evidence_level == "estimated"
        assert nutrition.confidence is not None
        assert nutrition.energy_kcal == Decimal(energy)
        assert nutrition.basis_reference == BURGER_KING_PRINGLES_ESTIMATE_VERSION


def test_burgerking_resolver_does_not_apply_to_other_merchants() -> None:
    assert (
        estimate_burgerking_nutrition(
            merchant_name="Outro Restaurante",
            item=_item("Steakhouse"),
        )
        is None
    )


def test_burgerking_configurable_bundles_are_not_meal_candidates() -> None:
    for name in (
        "Menu Double Spicy Krispper Grande",
        "Hambúrguer À Escolha + Batatas",
        "2 Hambúrgueres + Acompanhamento À Escolha + 2 Porções De Batatas Fritas",
        "King Jr.® Burger",
        "King Jr.® Cheeseburger",
        "King Jr.® Chicken Burger",
    ):
        assert is_non_meal_menu_item(
            name,
            merchant_name="Burger King (Colombo)",
        )


def test_burgerking_sides_and_snacks_are_not_meal_candidates() -> None:
    for name in (
        "Chili Cheese Bites X6",
        "Chicken Fries X6",
        "Cowboy King Fries Supreme",
        "Batata Grande + King Mix Pringles",
        "X4 Cheddar Bombs",
        "Nuggets X9 + King Mix Pringles",
    ):
        assert is_non_meal_menu_item(
            name,
            merchant_name="Burger King (Colombo)",
        )


def test_burgerking_standalone_burger_remains_a_meal_candidate() -> None:
    assert not is_non_meal_menu_item(
        "Steakhouse",
        description="Carne grelhada, tomate, queijo, cebola, alface, maionese e molho BBQ.",
        merchant_name="Burger King (Colombo)",
    )
