from decimal import Decimal

from app.services.external_dish_nutrition import is_non_meal_menu_item
from app.services.kfc_nutrition import KFC_NUTRITION_SOURCE, estimate_kfc_nutrition
from app.services.restaurant_menu_scraper import ScrapedMenuItem


def _item(name: str, description: str | None = None) -> ScrapedMenuItem:
    return ScrapedMenuItem(
        name=name,
        description=description,
        price=Decimal("10.00"),
        currency="EUR",
        energy_kcal=None,
        source_url="https://www.ubereats.com/pt/store/kfc-colombo/example",
    )


def _nutrient_value(nutrition, key: str) -> Decimal:
    return next(
        nutrient.value
        for nutrient in nutrition.nutrients
        if nutrient.key == key
    )


def test_kfc_hot_wings_scale_official_per_unit_nutrition() -> None:
    nutrition = estimate_kfc_nutrition(
        merchant_name="KFC (Colombo)",
        item=_item("Box 8 Hotwings"),
    )

    assert nutrition is not None
    assert nutrition.evidence_level == "official"
    assert nutrition.energy_kcal == Decimal(528)
    assert _nutrient_value(nutrition, "protein") == Decimal("54.4")
    assert nutrition.basis_reference == KFC_NUTRITION_SOURCE


def test_kfc_tenders_scale_official_per_unit_nutrition() -> None:
    nutrition = estimate_kfc_nutrition(
        merchant_name="KFC (Colombo)",
        item=_item("12 Tenders"),
    )

    assert nutrition is not None
    assert nutrition.energy_kcal == Decimal(912)
    assert _nutrient_value(nutrition, "protein") == Decimal("98.4")


def test_kfc_ocheddar_single_uses_official_nutrition() -> None:
    nutrition = estimate_kfc_nutrition(
        merchant_name="KFC (Colombo)",
        item=_item("O'Cheddar Single"),
    )

    assert nutrition is not None
    assert nutrition.energy_kcal == Decimal(579)
    assert _nutrient_value(nutrition, "protein") == Decimal("42.2")


def test_kfc_double_krunch_bbq_uses_official_nutrition() -> None:
    nutrition = estimate_kfc_nutrition(
        merchant_name="KFC (Colombo)",
        item=_item("Double Krunch BBQ"),
    )

    assert nutrition is not None
    assert nutrition.energy_kcal == Decimal(440)
    assert _nutrient_value(nutrition, "protein") == Decimal("30.1")


def test_kfc_configurable_bundles_are_not_meal_candidates() -> None:
    assert is_non_meal_menu_item(
        "Menu Wrap BoxMaster",
        description="1 Wrap Boxmaster + 1 Acompanhamento + 1 Bebida",
        merchant_name="KFC (Colombo)",
    )
    assert is_non_meal_menu_item(
        "Box 6 Tenders + 1 Molho Dip",
        description="6 Tiras de Peito de Frango + 1 Molho",
        merchant_name="KFC (Colombo)",
    )
    assert is_non_meal_menu_item(
        "Promoção 4ª Feira",
        description="9 pedaços ou 18 Hotwings ou 14 Tenders",
        merchant_name="KFC (Colombo)",
    )
    assert is_non_meal_menu_item(
        "Bucket 15 Hotwings Para 2",
        description="15 Asas + 2 Acompanhamentos + 2 Bebidas",
        merchant_name="KFC (Colombo)",
    )


def test_kfc_sides_and_unspecified_piece_mixes_are_not_meal_candidates() -> None:
    assert is_non_meal_menu_item(
        "Kentucky Fries O'Cheddar",
        merchant_name="KFC (Colombo)",
    )
    assert is_non_meal_menu_item("Batata Grande Palitos", merchant_name="KFC (Colombo)")
    assert is_non_meal_menu_item("8 Pedaços", merchant_name="KFC (Colombo)")
    assert not is_non_meal_menu_item("Box 8 Hotwings", merchant_name="KFC (Colombo)")
