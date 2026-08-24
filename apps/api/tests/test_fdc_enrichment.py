import json
from decimal import Decimal
from pathlib import Path

import pytest

from app.fdc_enrichment import _read_matches


def test_read_matches_accepts_explicit_usda_portion_mapping(tmp_path: Path) -> None:
    path = tmp_path / "matches.json"
    path.write_text(
        json.dumps(
            {
                "matches": [
                    {
                        "catalog_key": "legacy-v1:ingredient:meatball",
                        "fdc_id": 123,
                        "unit_portion_id": 456,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    matches = _read_matches(path)

    assert len(matches) == 1
    assert matches[0].catalog_key == "legacy-v1:ingredient:meatball"
    assert matches[0].fdc_id == 123
    assert matches[0].unit_portion_id == 456
    assert matches[0].recipe_unit == "un"
    assert matches[0].recipe_unit_quantity is None


def test_read_matches_accepts_explicit_recipe_unit_quantity(tmp_path: Path) -> None:
    path = tmp_path / "matches.json"
    path.write_text(
        json.dumps(
            {
                "matches": [
                    {
                        "catalog_key": "legacy-v1:ingredient:coconut-milk",
                        "fdc_id": 321,
                        "unit_portion_id": 654,
                        "recipe_unit": "ml",
                        "recipe_unit_quantity": "240",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    match = _read_matches(path)[0]

    assert match.recipe_unit == "ml"
    assert match.recipe_unit_quantity == Decimal(240)


def test_read_matches_rejects_recipe_unit_without_portion(tmp_path: Path) -> None:
    path = tmp_path / "matches.json"
    path.write_text(
        json.dumps(
            {
                "matches": [
                    {
                        "catalog_key": "legacy-v1:ingredient:example",
                        "fdc_id": 123,
                        "recipe_unit": "un",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="recipe_unit and recipe_unit_quantity require unit_portion_id",
    ):
        _read_matches(path)


def test_read_matches_rejects_recipe_unit_quantity_without_portion(
    tmp_path: Path,
) -> None:
    path = tmp_path / "matches.json"
    path.write_text(
        json.dumps(
            {
                "matches": [
                    {
                        "catalog_key": "legacy-v1:ingredient:example",
                        "fdc_id": 123,
                        "recipe_unit_quantity": "240",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="require unit_portion_id"):
        _read_matches(path)
