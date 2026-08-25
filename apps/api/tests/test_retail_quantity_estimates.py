from decimal import Decimal

from app.services.retail_quantity_estimates import estimate_retail_package_quantity


def test_known_supermarket_package_uses_retail_reference() -> None:
    estimate = estimate_retail_package_quantity(
        ingredient_name="Massa quebrada",
        composition_reference_unit="g",
        serving_count=Decimal(4),
    )

    assert estimate is not None
    assert estimate.reference_unit == "g"
    assert estimate.quantity_in_reference_unit == Decimal(230)
    assert estimate.source == "retail-reference"
    assert estimate.confidence == "medium"
    assert estimate.source_reference is not None
    assert "continente.pt" in estimate.source_reference


def test_unknown_package_scales_generic_estimate_to_recipe_servings() -> None:
    estimate = estimate_retail_package_quantity(
        ingredient_name="Ingrediente embalado desconhecido",
        composition_reference_unit="g",
        serving_count=Decimal(4),
    )

    assert estimate is not None
    assert estimate.reference_unit == "g"
    assert estimate.quantity_in_reference_unit == Decimal(400)
    assert estimate.source == "retail-heuristic"
    assert estimate.confidence == "low"


def test_unknown_volume_package_uses_volume_reference() -> None:
    estimate = estimate_retail_package_quantity(
        ingredient_name="Molho desconhecido",
        composition_reference_unit="ml",
        serving_count=Decimal(6),
    )

    assert estimate is not None
    assert estimate.reference_unit == "ml"
    assert estimate.quantity_in_reference_unit == Decimal(600)
