from decimal import Decimal

from app.services import fooddata_central


def test_search_parser_keeps_valid_generic_candidates() -> None:
    results = fooddata_central._parse_search_response(
        {
            "foods": [
                {
                    "fdcId": 123,
                    "description": "Garlic, raw",
                    "dataType": "Foundation",
                    "publicationDate": "4/1/2026",
                },
                {"fdcId": None, "description": "Broken", "dataType": "Foundation"},
            ]
        }
    )

    assert len(results) == 1
    assert results[0].fdc_id == 123
    assert results[0].description == "Garlic, raw"
    assert results[0].data_type == "Foundation"
    assert results[0].publication_date == "4/1/2026"


def test_food_parser_maps_energy_and_core_nutrients_per_100g() -> None:
    food = fooddata_central._parse_food_response(
        {
            "fdcId": 123,
            "description": "Garlic, raw",
            "dataType": "Foundation",
            "publicationDate": "4/1/2026",
            "foodNutrients": [
                {"nutrient": {"id": 1008, "unitName": "kcal"}, "amount": 149},
                {"nutrient": {"id": 1003, "unitName": "g"}, "amount": 6.36},
                {"nutrient": {"id": 1004, "unitName": "g"}, "amount": 0.5},
                {"nutrient": {"id": 1005, "unitName": "g"}, "amount": 33.06},
                {"nutrient": {"id": 1079, "unitName": "g"}, "amount": 2.1},
                {"nutrient": {"id": 1093, "unitName": "mg"}, "amount": 17},
            ],
        }
    )

    assert food.energy_kcal == Decimal("149")
    by_key = {nutrient.key: nutrient for nutrient in food.nutrients}
    assert by_key["protein"].value == Decimal("6.36")
    assert by_key["fat"].value == Decimal("0.5")
    assert by_key["carbohydrate"].value == Decimal("33.06")
    assert by_key["fiber"].value == Decimal("2.1")
    assert by_key["sodium"].value == Decimal("17")
    assert by_key["sodium"].unit == "mg"
    assert food.source_reference.endswith("/123/nutrients")


def test_food_parser_prefers_kcal_energy() -> None:
    food = fooddata_central._parse_food_response(
        {
            "fdcId": 456,
            "description": "Example food",
            "dataType": "SR Legacy",
            "foodNutrients": [
                {"nutrient": {"id": 1008, "unitName": "kcal"}, "amount": 88},
                {"nutrient": {"id": 2048, "unitName": "kcal"}, "amount": 91},
            ],
        }
    )

    assert food.energy_kcal == Decimal("88")
