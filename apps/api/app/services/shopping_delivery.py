"""Atomic, retry-safe partial shopping deliveries with separate expiry lots."""

import hashlib
import json
from datetime import UTC, datetime
from decimal import Decimal

from fastapi import HTTPException

from app.models.pantry_stock import PantryStockLot
from app.schemas.pantry_shopping import ShoppingReceiptBatchCreate
from app.services.pantry_shopping import _shopping_item, get_shopping_list, refresh_shopping_list
from app.services.serving_nutrition import UnsupportedUnitConversionError, convert_quantity
from app.services.shopping_receipt import validate_received_ingredient


def _number(value):
    return format(Decimal(value).normalize(), "f")


def receive_shopping_batch(db, family, item_id, data: ShoppingReceiptBatchCreate):
    item = _shopping_item(db, family.id, item_id)
    previous = item.pantry_receipt
    if previous and previous.get("format_version") != 2:
        raise HTTPException(409, "Esta compra já tem uma entrada concluída na despensa.")
    lots = []
    for lot in data.lots:
        if lot.expires_at and lot.expires_at.tzinfo is None:
            raise HTTPException(422, "Indique o fuso horário da validade.")
        lots.append(
            {
                "quantity": _number(lot.quantity),
                "unit": lot.unit.lower(),
                "location": lot.location or None,
                "expires_at": lot.expires_at.astimezone(UTC).isoformat()
                if lot.expires_at
                else None,
            }
        )
    payload = {
        "lots": lots,
        "complete": data.complete,
        "expected_quantity": _number(data.expected_quantity)
        if data.expected_quantity is not None
        else None,
    }
    fingerprint = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    batches = list(previous.get("batches", [])) if previous else []
    for batch in batches:
        if batch["request_id"] == str(data.request_id):
            if batch["fingerprint"] != fingerprint:
                raise HTTPException(
                    409, "Esta confirmação já foi usada com dados diferentes. Atualize as compras."
                )
            return get_shopping_list(db, family)
    if previous and previous["status"] == "complete":
        raise HTTPException(409, "Esta compra já tem a receção concluída.")
    if item.version != data.expected_version:
        raise HTTPException(409, "A compra mudou. Atualize a lista antes de registar a entrada.")
    if item.status != "purchased" or item.food_item_id is None:
        raise HTTPException(422, "Assinale a compra e associe um ingrediente antes da entrada.")
    if len(batches) >= 32 and lots:
        raise HTTPException(
            409, "Limite de receções desta compra atingido. Use os lotes da despensa."
        )
    if not lots and not previous:
        raise HTTPException(422, "A primeira entrada precisa de pelo menos um lote.")
    # Closing an existing delivery without more stock does not certify a new label.
    if lots:
        validate_received_ingredient(db, family, item)
    received_quantity = Decimal(previous["quantity"]) if previous else Decimal(0)
    try:
        received_quantity += sum(
            (convert_quantity(Decimal(lot["quantity"]), lot["unit"], item.unit) for lot in lots),
            Decimal(0),
        )
    except UnsupportedUnitConversionError as exc:
        raise HTTPException(
            422, "Use unidades compatíveis com o ingrediente, sem estimar densidades."
        ) from exc
    expected = (
        Decimal(previous["expected_quantity"])
        if previous and previous.get("expected_quantity") is not None
        else data.expected_quantity
    )
    if previous and data.expected_quantity is not None and data.expected_quantity != expected:
        raise HTTPException(
            409, "O total esperado já foi confirmado. Conclua a receção se não vai chegar mais."
        )
    if not data.complete and (expected is None or received_quantity >= expected):
        raise HTTPException(
            422, "Indique um total esperado superior ao recebido ou conclua a receção."
        )
    if received_quantity > Decimal("9999999999.9999"):
        raise HTTPException(422, "A quantidade acumulada excede o limite do inventário.")
    now = datetime.now(UTC)
    recorded_lots = []
    for index, (row, values) in enumerate(zip(data.lots, lots, strict=True)):
        lot = PantryStockLot(
            family_id=family.id,
            food_item_id=item.food_item_id,
            stock_key=f"shopping:{item.id}:{data.request_id}:{index}",
            quantity_available=row.quantity,
            unit=values["unit"],
            location=values["location"],
            expires_at=row.expires_at,
            observed_at=now,
            is_available=True,
            source="shopping_receipt",
            source_reference=str(item.id),
        )
        db.add(lot)
        db.flush()
        recorded_lots.append({**values, "lot_id": str(lot.id)})
    batches.append(
        {
            "request_id": str(data.request_id),
            "fingerprint": fingerprint,
            "received_at": now.isoformat(),
            "lots": recorded_lots,
            "complete": data.complete,
        }
    )
    item.pantry_receipt = {
        "format_version": 2,
        "status": "complete" if data.complete else "partial",
        "quantity": _number(received_quantity),
        "unit": item.unit,
        "expected_quantity": _number(expected) if expected is not None else None,
        "remaining_quantity": _number(max(Decimal(0), expected - received_quantity))
        if expected is not None
        else "0",
        "received_at": now.isoformat(),
        "batches": batches,
        "product_selection": previous.get("product_selection")
        if previous
        else item.product_selection,
    }
    item.item_key = f"received:{item.id}"
    item.version += 1
    # Production sessions use autoflush=False; refresh must not overwrite pending history.
    db.flush()
    shopping_list = item.shopping_list
    if shopping_list.planning_start and shopping_list.planning_end:
        return refresh_shopping_list(
            db,
            family,
            start_date=shopping_list.planning_start,
            days=(shopping_list.planning_end - shopping_list.planning_start).days + 1,
        )
    db.commit()
    return get_shopping_list(db, family)
