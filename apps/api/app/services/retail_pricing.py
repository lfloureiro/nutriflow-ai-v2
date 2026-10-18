"""Comparable observed retail prices; no clinical or recipe equivalence inferred."""

from decimal import Decimal, InvalidOperation

from app.schemas.planning_workspace import RetailUnitPriceRead
from app.services.serving_nutrition import convert_quantity


def retail_unit_price(pack_quantity, pack_unit: str, observed_price) -> RetailUnitPriceRead:
    unit = pack_unit.strip().lower()
    reference = "kg" if unit in {"mg", "g", "kg"} else "l" if unit in {"ml", "l"} else None
    if reference is None:
        return RetailUnitPriceRead(issue="unit_not_comparable")
    try:
        quantity = Decimal(str(pack_quantity))
        if not quantity.is_finite() or quantity <= 0:
            raise ValueError
    except (ValueError, InvalidOperation):
        return RetailUnitPriceRead(reference_unit=reference, issue="invalid_pack")
    if observed_price is None:
        return RetailUnitPriceRead(reference_unit=reference, issue="price_unavailable")
    try:
        price = Decimal(str(observed_price))
        if not price.is_finite() or price < 0:
            raise ValueError
        value = price / convert_quantity(quantity, unit, reference)
        return RetailUnitPriceRead(
            reference_unit=reference, unit_price=value.quantize(Decimal("0.000001"))
        )
    except (ValueError, InvalidOperation, ZeroDivisionError):
        return RetailUnitPriceRead(reference_unit=reference, issue="invalid_price")
