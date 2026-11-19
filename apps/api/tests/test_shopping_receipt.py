# ruff: noqa: F811
from decimal import Decimal

import pytest

from tests.test_pantry_shopping_api import _request
from tests.test_retail_purchase import (  # noqa: F401
    _effective_variant_shopping,
    retail_context,
)


def _purchased(db, context):
    item, _, _ = _effective_variant_shopping(db, context)
    path = context[3]
    response = _request(
        db, "PATCH", path + f"/shopping-list/items/{item['id']}", json={"status": "purchased"}
    )
    assert response.status_code == 200, response.text
    return response.json()["items"][0]


def test_receipt_actual_quantity_idempotence_and_provenance(db_session, retail_context):
    item = _purchased(db_session, retail_context)
    path = retail_context[3]
    endpoint = path + f"/shopping-list/items/{item['id']}/receipt"
    before = _request(db_session, "GET", path + "/pantry").json()
    assert len(before) == 1  # Merely checking purchased never adds stock.
    payload = {
        "expected_version": item["version"],
        "quantity": "1500",
        "unit": "g",
        "location": "Armário",
        "label_reviewed": True,
    }
    received = _request(db_session, "POST", endpoint, json=payload)
    assert received.status_code == 200, received.text
    receipt = received.json()["items"][0]["pantry_receipt"]
    assert Decimal(receipt["quantity"]) == 1500
    assert received.json()["requirements"][0]["missing_quantity"] == "0"
    retry = _request(db_session, "POST", endpoint, json=payload)
    assert retry.status_code == 200 and retry.json()["items"][0]["pantry_receipt"] == receipt
    assert len(_request(db_session, "GET", path + "/pantry").json()) == 2
    assert (
        _request(db_session, "POST", endpoint, json={**payload, "quantity": "2000"}).status_code
        == 409
    )
    assert (
        _request(
            db_session,
            "PATCH",
            path + f"/shopping-list/items/{item['id']}",
            json={"status": "needed"},
        ).status_code
        == 409
    )
    assert (
        _request(db_session, "DELETE", path + f"/shopping-list/items/{item['id']}").status_code
        == 409
    )
    # Editing/deactivating a lot cannot cause a retry to recreate the original stock.
    _request(db_session, "DELETE", path + f"/pantry/{receipt['lot_id']}")
    assert _request(db_session, "POST", endpoint, json=payload).status_code == 200
    assert len(_request(db_session, "GET", path + "/pantry").json()) == 1


@pytest.mark.parametrize(
    "change,status",
    [
        ({"expected_version": 999}, 409),
        ({"unit": "ml"}, 422),
        ({"quantity": "0"}, 422),
        ({"label_reviewed": False}, 422),
        ({"expires_at": "2030-01-10T10:00:00"}, 422),
    ],
)
def test_receipt_rejects_invalid_or_stale_input(db_session, retail_context, change, status):
    item = _purchased(db_session, retail_context)
    path = retail_context[3]
    payload = {
        "expected_version": item["version"],
        "quantity": "1.5",
        "unit": "kg",
        "label_reviewed": True,
        **change,
    }
    response = _request(
        db_session, "POST", path + f"/shopping-list/items/{item['id']}/receipt", json=payload
    )
    assert response.status_code == status, response.text
    assert len(_request(db_session, "GET", path + "/pantry").json()) == 1


def test_receipt_family_isolation_and_changed_label(db_session, retail_context):
    import uuid

    from app.models.planning_workspace import RetailAlternative

    item = _purchased(db_session, retail_context)
    _family, other, _, path, product, _ = retail_context
    payload = {
        "expected_version": item["version"],
        "quantity": "1.5",
        "unit": "kg",
        "label_reviewed": True,
    }
    assert (
        _request(
            db_session,
            "POST",
            f"/api/families/{other.id}/shopping-list/items/{item['id']}/receipt",
            json=payload,
        ).status_code
        == 404
    )
    row = db_session.get(RetailAlternative, uuid.UUID(product["id"]))
    row.ingredient_summary = "Changed ingredients"
    db_session.flush()
    response = _request(
        db_session, "POST", path + f"/shopping-list/items/{item['id']}/receipt", json=payload
    )
    assert response.status_code == 409, response.text


def test_receipt_replenishment_creates_new_needed_item_and_keeps_history(db_session, retail_context):
    item = _purchased(db_session, retail_context)
    path = retail_context[3]
    payload = {"expected_version":item["version"],"quantity":"1.5","unit":"kg","label_reviewed":True}
    received = _request(db_session,"POST",path+f"/shopping-list/items/{item['id']}/receipt",json=payload)
    assert received.status_code == 200, received.text
    lot_id = received.json()["items"][0]["pantry_receipt"]["lot_id"]
    _request(db_session,"DELETE",path+f"/pantry/{lot_id}")
    refreshed = _request(db_session,"POST",path+"/shopping-list/refresh",json={"start_date":"2030-01-07","days":7})
    assert refreshed.status_code == 200, refreshed.text
    rows = refreshed.json()["items"]
    assert len(rows) == 2
    assert len([r for r in rows if r["pantry_receipt"]]) == 1
    needed = next(r for r in rows if r["status"] == "needed")
    assert needed["id"] != item["id"] and Decimal(needed["quantity"]) == 1100
