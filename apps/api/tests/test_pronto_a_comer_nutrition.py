from decimal import Decimal

from app.services.external_dish_nutrition import is_non_meal_menu_item
from app.services.pronto_a_comer_nutrition import (
    PRONTO_A_COMER_ESTIMATE_VERSION,
    estimate_pronto_a_comer_nutrition,
)
from app.services.restaurant_menu_scraper import ScrapedMenuItem


def _item(name: str, description: str | None = None) -> ScrapedMenuItem:
    return ScrapedMenuItem(
        name=name,
        description=description,
        price=Decimal("10.00"),
        currency="EUR",
        energy_kcal=None,
        source_url="https://www.ubereats.com/pt/store/pronto-a-comer-de-carnaxide/example",
    )


def _nutrient_value(nutrition, key: str) -> Decimal:
    return next(
        nutrient.value
        for nutrient in nutrition.nutrients
        if nutrient.key == key
    )


def test_pronto_a_comer_current_main_dishes_use_curated_structural_estimates() -> None:
    expected = {
        "Bacalhau à Brás": ("650", "32"),
        "Meio Frango Assado": ("650", "65"),
        "Caldeirada de Polvo c/ Batata Doce": ("550", "35"),
        "Perna de Porco Assada": ("600", "45"),
        "Coelho Assado c/ Batatas": ("620", "45"),
        "Arroz de Tamboril": ("600", "35"),
        "Robalo Grelhado c/ Batata": ("520", "40"),
        "Vitela c/ Cogumelos": ("560", "40"),
        "Choquinhos à Algarvia": ("520", "35"),
        "Costeletas de Porco à Salsicheiro": ("700", "45"),
    }

    for name, (energy, protein) in expected.items():
        nutrition = estimate_pronto_a_comer_nutrition(
            merchant_name="Pronto a Comer de Carnaxide",
            item=_item(name),
        )
        assert nutrition is not None
        assert nutrition.evidence_level == "estimated"
        assert nutrition.confidence is not None
        assert nutrition.energy_kcal == Decimal(energy)
        assert _nutrient_value(nutrition, "protein") == Decimal(protein)
        assert nutrition.basis_reference == PRONTO_A_COMER_ESTIMATE_VERSION


def test_pronto_a_comer_estimator_does_not_apply_to_other_merchants() -> None:
    assert (
        estimate_pronto_a_comer_nutrition(
            merchant_name="Outro Restaurante",
            item=_item("Bacalhau à Brás"),
        )
        is None
    )


def test_pronto_a_comer_non_meal_items_are_filtered() -> None:
    for name in (
        "Frango Assado",
        "Sopa de Nabiças",
        "Canja de Galinha",
        "Arroz Branco",
        "Feijão Verde Salteado",
        "Esparregado",
        "Rissol de Camarão",
        "Chamuça",
        "Croquete",
        "Pastel de Massa Tenra",
        "Pastel de Bacalhau",
        "Empada",
        "Arroz Doce",
        "Serradura",
        "Pudim de Ovos",
        "Bola de Água",
        "Palito",
        "Bola de Centeio",
        "Pão com Chouriço",
        "Pão de Sementes",
        "Pegões Branco",
        "Mateus Rose",
        "Guaraná lata",
        "7Up 1.5L",
        "Compal Frutos Vermelhos 1L",
    ):
        assert is_non_meal_menu_item(
            name,
            merchant_name="Pronto a Comer de Carnaxide",
        )


def test_pronto_a_comer_main_dish_remains_candidate() -> None:
    assert not is_non_meal_menu_item(
        "Robalo Grelhado c/ Batata",
        description="Acompanha com batata cozida",
        merchant_name="Pronto a Comer de Carnaxide",
    )
