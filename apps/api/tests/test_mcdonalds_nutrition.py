from decimal import Decimal

from app.services.external_dish_nutrition import is_non_meal_menu_item
from app.services.mcdonalds_nutrition import estimate_mcdonalds_nutrition
from app.services.restaurant_menu_scraper import ScrapedMenuItem


def _item(name: str) -> ScrapedMenuItem:
    return ScrapedMenuItem(
        name=name,
        description=None,
        price=Decimal("10.00"),
        currency="EUR",
        energy_kcal=None,
        source_url="https://www.ubereats.com/pt/store/mcdonalds/example",
    )


def _nutrient_value(nutrition, key: str) -> Decimal:
    return next(
        nutrient.value
        for nutrient in nutrition.nutrients
        if nutrient.key == key
    )


def test_big_mac_uses_official_portugal_nutrition() -> None:
    nutrition = estimate_mcdonalds_nutrition(
        merchant_name="McDonald's® (Venda Nova)",
        item=_item("Big Mac®"),
    )

    assert nutrition is not None
    assert nutrition.evidence_level == "official"
    assert nutrition.energy_kcal == Decimal(544)
    assert _nutrient_value(nutrition, "protein") == Decimal(27)
    assert _nutrient_value(nutrition, "sodium") == Decimal(920)


def test_world_menu_heist_items_use_current_official_nutrition() -> None:
    teriyaki = estimate_mcdonalds_nutrition(
        merchant_name="McDonald's® (Venda Nova)",
        item=_item("McCrispy Teriyaki"),
    )
    philly = estimate_mcdonalds_nutrition(
        merchant_name="McDonald's® (Venda Nova)",
        item=_item("Philly Cheese Stack Double"),
    )

    assert teriyaki is not None
    assert teriyaki.energy_kcal == Decimal(630)
    assert _nutrient_value(teriyaki, "protein") == Decimal(26)
    assert philly is not None
    assert philly.energy_kcal == Decimal(832)
    assert _nutrient_value(philly, "protein") == Decimal(48)


def test_garlic_pepper_nuggets_uber_name_maps_to_official_product() -> None:
    nutrition = estimate_mcdonalds_nutrition(
        merchant_name="McDonald's® (Venda Nova)",
        item=_item("Garlic & Pepper McNuggets 10"),
    )

    assert nutrition is not None
    assert nutrition.energy_kcal == Decimal(445)
    assert _nutrient_value(nutrition, "sodium") == Decimal(1080)


def test_mcdonalds_unknown_product_is_not_given_fake_official_nutrition() -> None:
    nutrition = estimate_mcdonalds_nutrition(
        merchant_name="McDonald's® (Venda Nova)",
        item=_item("Produto Temporário Desconhecido"),
    )

    assert nutrition is None


def test_mcdonalds_catalog_does_not_apply_to_other_merchants() -> None:
    nutrition = estimate_mcdonalds_nutrition(
        merchant_name="Burger King",
        item=_item("Big Mac"),
    )

    assert nutrition is None


def test_configurable_bundles_and_desserts_do_not_enter_meal_ranking() -> None:
    assert is_non_meal_menu_item("Happy Meal® Cheeseburger")
    assert is_non_meal_menu_item("McMenu® 2 Snack Wraps")
    assert is_non_meal_menu_item("Chicken Share Box Original")
    assert is_non_meal_menu_item("McFlurry® Popcorn")
    assert not is_non_meal_menu_item("McCrispy Teriyaki")
