# ruff: noqa: F811
import uuid
from decimal import Decimal

import pytest

from tests.test_pantry_shopping_api import _request
from tests.test_retail_purchase import _select, retail_context  # noqa: F401
from tests.test_shopping_receipt import _purchased


@pytest.fixture(autouse=True)
def production_flush_behavior(db_session):
    db_session.autoflush = False


def _payload(item, lots=None, **changes):
    return {
        "request_id": str(uuid.uuid4()),
        "expected_version": item["version"],
        "lots": lots if lots is not None else [{"quantity": "400", "unit": "g"}],
        "complete": False,
        "expected_quantity": "1500",
        "label_reviewed": True,
        **changes,
    }


def _receive(db, path, item, payload):
    return _request(db, "POST", path + f"/shopping-list/items/{item['id']}/receipts", json=payload)


def _history(response, item):
    return next(i for i in response.json()["items"] if i["id"] == item["id"])


def test_partial_delivery_tracks_incoming_separately_then_closes_shortfall(
    db_session, retail_context
):
    item = _purchased(db_session, retail_context)
    path = retail_context[3]
    first_payload = _payload(item)
    first = _receive(db_session, path, item, first_payload)
    assert first.status_code == 200, first.text
    received = _history(first, item)
    assert received["pantry_receipt"]["status"] == "partial"
    req = first.json()["requirements"][0]
    assert Decimal(req["available_quantity"]) == 500
    assert Decimal(req["missing_quantity"]) == 700
    assert Decimal(req["incoming_quantity"]) == 1100
    assert Decimal(req["to_buy_quantity"]) == 0
    assert not any(i["status"] == "needed" for i in first.json()["items"])
    second_payload = _payload(
        received,
        lots=[{"quantity": "0.5", "unit": "kg", "expires_at": "2030-02-01T23:59:59Z"}],
        expected_quantity=None,
    )
    second = _receive(db_session, path, received, second_payload)
    assert second.status_code == 200, second.text
    received = _history(second, item)
    assert Decimal(received["pantry_receipt"]["quantity"]) == 900
    assert Decimal(received["pantry_receipt"]["remaining_quantity"]) == 600
    finish = _receive(
        db_session,
        path,
        received,
        _payload(received, lots=[], complete=True, expected_quantity=None),
    )
    assert finish.status_code == 200, finish.text
    receipt = _history(finish, item)["pantry_receipt"]
    assert receipt["status"] == "complete" and len(receipt["batches"]) == 3
    req = finish.json()["requirements"][0]
    assert Decimal(req["available_quantity"]) == 1000
    assert Decimal(req["incoming_quantity"]) == 0
    assert Decimal(req["to_buy_quantity"]) == 200
    assert (
        Decimal(next(i for i in finish.json()["items"] if i["status"] == "needed")["quantity"])
        == 200
    )
    # Retry any earlier delivery after closure remains idempotent, even after stock deactivation.
    first_lot = receipt["batches"][0]["lots"][0]["lot_id"]
    _request(db_session, "DELETE", path + f"/pantry/{first_lot}")
    before = len(_request(db_session, "GET", path + "/pantry").json())
    retry = _receive(db_session, path, item, first_payload)
    assert retry.status_code == 200
    assert _history(retry, item)["pantry_receipt"] == receipt
    assert len(_request(db_session, "GET", path + "/pantry").json()) == before
    assert (
        _receive(
            db_session, path, item, {**first_payload, "lots": [{"quantity": "401", "unit": "g"}]}
        ).status_code
        == 409
    )


def test_split_lots_keep_separate_expiry_and_storage_and_refresh_remaining_buy(
    db_session, retail_context
):
    item = _purchased(db_session, retail_context)
    path = retail_context[3]
    payload = _payload(
        item,
        lots=[
            {
                "quantity": "500",
                "unit": "g",
                "location": "Armário A",
                "expires_at": "2030-02-01T23:59:59Z",
            },
            {
                "quantity": "0.5",
                "unit": "kg",
                "location": "Armário B",
                "expires_at": "2030-03-01T23:59:59Z",
            },
        ],
        complete=True,
        expected_quantity=None,
    )
    result = _receive(db_session, path, item, payload)
    assert result.status_code == 200, result.text
    receipt = _history(result, item)["pantry_receipt"]
    assert Decimal(receipt["quantity"]) == 1000
    lots = receipt["batches"][0]["lots"]
    assert len({l["lot_id"] for l in lots}) == 2
    assert {l["location"] for l in lots} == {"Armário A", "Armário B"}
    assert len({l["expires_at"] for l in lots}) == 2
    assert Decimal(result.json()["requirements"][0]["available_quantity"]) == 1100
    assert (
        Decimal(next(i for i in result.json()["items"] if i["status"] == "needed")["quantity"])
        == 100
    )
    retry = _receive(db_session, path, item, payload)
    assert (
        retry.status_code == 200 and len(_request(db_session, "GET", path + "/pantry").json()) == 3
    )


@pytest.mark.parametrize(
    "changes,status",
    [
        ({"expected_quantity": None}, 422),
        ({"expected_quantity": "300"}, 422),
        ({"expected_version": 999}, 409),
        ({"label_reviewed": False}, 422),
        ({"lots": [], "complete": True}, 422),
        ({"lots": [{"quantity": "100", "unit": "g"}, {"quantity": "1", "unit": "ml"}]}, 422),
        (
            {
                "lots": [
                    {"quantity": "100", "unit": "g"},
                    {"quantity": "1", "unit": "g", "expires_at": "2030-01-01T10:00:00"},
                ]
            },
            422,
        ),
        ({"lots": [{"quantity": "1", "unit": "g"}] * 21}, 422),
    ],
)
def test_invalid_delivery_is_atomic(db_session, retail_context, changes, status):
    item = _purchased(db_session, retail_context)
    path = retail_context[3]
    result = _receive(db_session, path, item, _payload(item, **changes))
    assert result.status_code == status, result.text
    assert len(_request(db_session, "GET", path + "/pantry").json()) == 1
    current = _request(db_session, "GET", path + "/shopping-list").json()["items"][0]
    assert current["version"] == item["version"] and not current["pantry_receipt"]


def test_partial_reception_family_scope_version_and_label_changes(db_session, retail_context):
    from app.models.planning_workspace import RetailAlternative

    item = _purchased(db_session, retail_context)
    path = retail_context[3]
    other = retail_context[1]
    payload = _payload(item)
    foreign = _receive(db_session, f"/api/families/{other.id}", item, payload)
    assert foreign.status_code == 404
    first = _receive(db_session, path, item, payload)
    assert first.status_code == 200, first.text
    current = _history(first, item)
    assert _receive(db_session, path, item, _payload(item)).status_code == 409
    product = db_session.get(RetailAlternative, uuid.UUID(retail_context[4]["id"]))
    product.ingredient_summary = "Altered label"
    db_session.flush()
    assert (
        _receive(db_session, path, current, _payload(current, expected_quantity=None)).status_code
        == 409
    )
    finish = _receive(
        db_session, path, current, _payload(current, lots=[], complete=True, expected_quantity=None)
    )
    assert finish.status_code == 200, finish.text
    assert _history(finish, item)["pantry_receipt"]["status"] == "complete"
    assert len(_request(db_session, "GET", path + "/pantry").json()) == 2


def test_package_preview_uses_buy_quantity_after_expected_delivery(db_session, retail_context):
    item = _purchased(db_session, retail_context)
    path = retail_context[3]
    product = retail_context[4]
    response = _receive(
        db_session,
        path,
        item,
        _payload(item, lots=[{"quantity": "200", "unit": "g"}], expected_quantity="500"),
    )
    assert response.status_code == 200, response.text
    req = response.json()["requirements"][0]
    assert Decimal(req["missing_quantity"]) == 900 and Decimal(req["incoming_quantity"]) == 300
    needed = next(i for i in response.json()["items"] if i["status"] == "needed")
    assert Decimal(needed["quantity"]) == 600
    selected = _select(db_session, path, product, needed)
    assert selected.status_code == 200, selected.text
    current = next(i for i in selected.json()["items"] if i["id"] == needed["id"])
    assert current["product_selection"]["package_count"] == 2
    assert current["product_selection"]["status"] == "confirmed"


@pytest.mark.parametrize("legacy_first", [True, False])
def test_legacy_and_multi_receipt_protocols_cannot_duplicate_each_other(
    db_session, retail_context, legacy_first
):
    item = _purchased(db_session, retail_context)
    path = retail_context[3]
    old = {
        "expected_version": item["version"],
        "quantity": "400",
        "unit": "g",
        "label_reviewed": True,
    }
    if legacy_first:
        first = _request(
            db_session, "POST", path + f"/shopping-list/items/{item['id']}/receipt", json=old
        )
        assert first.status_code == 200, first.text
        result = _receive(db_session, path, _history(first, item), _payload(_history(first, item)))
    else:
        first = _receive(db_session, path, item, _payload(item))
        assert first.status_code == 200, first.text
        result = _request(
            db_session, "POST", path + f"/shopping-list/items/{item['id']}/receipt", json=old
        )
    assert result.status_code == 409, result.text
    assert len(_request(db_session, "GET", path + "/pantry").json()) == 2


def test_expired_lots_do_not_satisfy_the_planned_meal(db_session, retail_context):
    item = _purchased(db_session, retail_context)
    path = retail_context[3]
    payload = _payload(
        item,
        lots=[
            {"quantity": "500", "unit": "g", "expires_at": "2030-01-06T23:59:59Z"},
            {"quantity": "500", "unit": "g", "expires_at": "2031-01-06T23:59:59Z"},
        ],
        complete=True,
        expected_quantity=None,
    )
    response = _receive(db_session, path, item, payload)
    assert response.status_code == 200, response.text
    req = response.json()["requirements"][0]
    assert Decimal(req["available_quantity"]) == 600
    assert Decimal(req["to_buy_quantity"]) == 600
    assert Decimal(_history(response, item)["pantry_receipt"]["quantity"]) == 1000


def test_stock_expiring_between_meals_is_allocated_only_once_before_expiry(
    db_session, retail_context
):
    from sqlalchemy import select

    from app.models import MealEvent
    from app.models.meal import MealParticipant, Serving

    item = _purchased(db_session, retail_context)
    path = retail_context[3]
    recipe_id = db_session.scalar(
        select(Serving.recipe_id)
        .join(Serving.meal_participant)
        .join(MealParticipant.meal_event)
        .where(MealEvent.family_id == retail_context[0].id)
        .limit(1)
    )
    added = _request(
        db_session,
        "POST",
        path + "/meal-plan",
        json={
            "date": "2030-01-09",
            "local_time": "20:00",
            "meal_type": "dinner",
            "recipe_id": str(recipe_id),
            "participants": [
                {"person_id": str(p.id), "quantity": "1", "unit": "serving"}
                for p in retail_context[2]
            ],
        },
    )
    assert added.status_code == 201, added.text
    response = _receive(
        db_session,
        path,
        item,
        _payload(
            item,
            lots=[{"quantity": "2000", "unit": "g", "expires_at": "2030-01-08T23:59:59Z"}],
            complete=True,
            expected_quantity=None,
        ),
    )
    assert response.status_code == 200, response.text
    req = response.json()["requirements"][0]
    assert Decimal(req["required_quantity"]) == 2400
    assert Decimal(req["available_quantity"]) == 1300
    assert Decimal(req["missing_quantity"]) == 1100
    pantry = _request(db_session, "GET", path + "/pantry").json()
    assert any(Decimal(l["quantity_available"]) == 2000 for l in pantry)


def test_delivery_limit_still_allows_closing_without_more_stock(db_session, retail_context):
    item = _purchased(db_session, retail_context)
    path = retail_context[3]
    current = item
    for _ in range(32):
        response = _receive(
            db_session,
            path,
            current,
            _payload(
                current,
                lots=[{"quantity": "1", "unit": "g"}],
                expected_quantity="1500" if not current.get("pantry_receipt") else None,
            ),
        )
        assert response.status_code == 200, response.text
        current = _history(response, item)
    blocked = _receive(
        db_session,
        path,
        current,
        _payload(current, lots=[{"quantity": "1", "unit": "g"}], expected_quantity=None),
    )
    assert blocked.status_code == 409, blocked.text
    finish = _receive(
        db_session, path, current, _payload(current, lots=[], complete=True, expected_quantity=None)
    )
    assert finish.status_code == 200, finish.text
    receipt = _history(finish, item)["pantry_receipt"]
    assert receipt["status"] == "complete" and len(receipt["batches"]) == 33
    assert len(_request(db_session, "GET", path + "/pantry").json()) == 33
