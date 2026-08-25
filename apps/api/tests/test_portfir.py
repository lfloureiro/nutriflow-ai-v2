from decimal import Decimal
from pathlib import Path

from openpyxl import Workbook

from app.services.portfir import load_portfir_foods


def _workbook(path: Path) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "TCA"
    sheet.append(["Tabela da Composição de Alimentos"])
    sheet.append(
        [
            "ID",
            "Nome",
            "Energia (kcal)",
            "Proteína (g)",
            "Lípidos (g)",
            "Hidratos de carbono (g)",
            "Fibra (g)",
            "Sódio (mg)",
        ]
    )
    sheet.append([101, "Azeite", 899, 0, 99.9, 0, 0, 0])
    sheet.append([102, "Cebola, crua", 29, 1.2, 0.2, 5.2, 1.4, 9])
    workbook.save(path)


def test_portfir_loader_finds_food_table_and_nutrients(tmp_path: Path) -> None:
    path = tmp_path / "portfir.xlsx"
    _workbook(path)

    foods = load_portfir_foods(path)

    assert len(foods) == 2
    olive_oil = foods[0]
    assert olive_oil.code == "101"
    assert olive_oil.name == "Azeite"
    assert olive_oil.energy_kcal == Decimal(899)
    by_key = {nutrient.key: nutrient for nutrient in olive_oil.nutrients}
    assert by_key["fat"].value == Decimal("99.9")
    assert by_key["fat"].unit == "g"

    onion = foods[1]
    assert onion.name == "Cebola, crua"
    assert onion.energy_kcal == Decimal(29)
    onion_nutrients = {nutrient.key: nutrient for nutrient in onion.nutrients}
    assert onion_nutrients["protein"].value == Decimal("1.2")
    assert onion_nutrients["sodium"].value == Decimal(9)
    assert onion_nutrients["sodium"].unit == "mg"
