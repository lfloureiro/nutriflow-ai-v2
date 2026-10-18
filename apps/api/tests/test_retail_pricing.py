from decimal import Decimal

import pytest

from app.retail_alternatives_seed import import_retail_observations
from app.services.retail_pricing import retail_unit_price
from tests.test_pantry_shopping_api import _request
from tests.test_planning_workspace import _family


@pytest.mark.parametrize(
    "quantity,unit,price,reference,expected",
    [
        ("500", "g", "1.75", "kg", "3.50"),
        ("400", "g", "3.08", "kg", "7.70"),
        ("0.5", "kg", "1.75", "kg", "3.50"),
        ("200", "ml", "0.85", "l", "4.25"),
        ("6", "l", "7.50", "l", "1.25"),
        ("500000", "mg", "1.75", "kg", "3.50"),
        ("500", " G ", "0", "kg", "0"),
    ],
)
def test_observed_unit_prices_normalize_only_physical_units(
    quantity, unit, price, reference, expected
):
    result = retail_unit_price(quantity, unit, price)
    assert result.reference_unit == reference
    assert result.unit_price == Decimal(expected)
    assert result.issue is None


@pytest.mark.parametrize(
    "quantity,unit,price,issue",
    [
        ("500", "g", None, "price_unavailable"),
        ("500", "un", "1.75", "unit_not_comparable"),
        ("0", "g", "1.75", "invalid_pack"),
        ("NaN", "g", "1.75", "invalid_pack"),
        ("500", "ml", "NaN", "invalid_price"),
        ("500", "g", "-1", "invalid_price"),
    ],
)
def test_unavailable_prices_or_unknown_pack_weights_are_not_zero(quantity, unit, price, issue):
    result = retail_unit_price(quantity, unit, price)
    assert result.unit_price is None and result.issue == issue


def test_comparison_response_preserves_source_evidence_and_family_scope(db_session):
    family, other, _, food, _ = _family(db_session)
    import_retail_observations(db_session)
    response = _request(db_session, "GET", f"/api/families/{family.id}/retail-alternatives")
    assert response.status_code == 200, response.text
    pasta = [p for p in response.json() if p["alternative_group"] == "rice-corn-pasta"]
    assert len(pasta) == 2
    assert {Decimal(p["price_comparison"]["unit_price"]) for p in pasta} == {
        Decimal("3.5"),
        Decimal("7.7"),
    }
    assert all(p["price_comparison"]["reference_unit"] == "kg" for p in pasta)
    assert all(str(food.id) in p["applicable_food_item_ids"] for p in pasta)
    assert len({p["evidence_level"] for p in pasta}) == 2
    assert all(p["product_url"].startswith("https://") and p["observed_on"] for p in pasta)
    assert not any(p["confirmed_food_item_id"] for p in pasta)
    usable = next(p for p in pasta if p["ingredient_confirmation_issue"] is None)
    confirmation = _request(
        db_session,
        "POST",
        f"/api/families/{family.id}/retail-alternatives/{usable['id']}/confirm-ingredient",
        json={"expected_fingerprint": usable["evidence_fingerprint"], "label_reviewed": True},
    )
    assert confirmation.status_code == 200, confirmation.text
    private_food_id = confirmation.json()["food_item_id"]
    own = _request(db_session, "GET", f"/api/families/{family.id}/retail-alternatives").json()
    assert any(p["confirmed_food_item_id"] == private_food_id for p in own)
    foreign = _request(db_session, "GET", f"/api/families/{other.id}/retail-alternatives")
    assert foreign.status_code == 200
    assert all(not p["confirmed_food_item_id"] for p in foreign.json())
    assert all(private_food_id not in p["applicable_food_item_ids"] for p in foreign.json())
