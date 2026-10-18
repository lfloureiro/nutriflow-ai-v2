"""Explicit, atomic receipt of a shopping item into an actual pantry lot."""

from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import select

from app.models.pantry_stock import PantryStockLot
from app.models.retail_confirmation import RetailIngredientConfirmation
from app.schemas.pantry_shopping import ShoppingReceiptCreate
from app.services.pantry_shopping import _pantry_food, _shopping_item, get_shopping_list
from app.services.retail_purchase import confirmation_current
from app.services.serving_nutrition import UnsupportedUnitConversionError, convert_quantity


def receive_shopping_item(db, family, item_id, data: ShoppingReceiptCreate):

    item = _shopping_item(db, family.id, item_id)
    if data.expires_at and data.expires_at.tzinfo is None:
        raise HTTPException(422, "Indique o fuso horário da validade.")
    received = {
        "quantity": format(data.quantity.normalize(), "f"),
        "unit": data.unit.lower(),
        "location": data.location or None,
        "expires_at": data.expires_at.astimezone(UTC).isoformat() if data.expires_at else None,
    }
    if item.pantry_receipt:
        if all(item.pantry_receipt.get(k) == v for k, v in received.items()):
            return get_shopping_list(db, family)
        raise HTTPException(409, "Esta compra já entrou na despensa. Corrija o lote na despensa.")
    if item.version != data.expected_version:
        raise HTTPException(409, "A compra mudou. Atualize a lista antes de registar a entrada.")
    if item.status != "purchased" or item.food_item_id is None:
        raise HTTPException(422, "Assinale a compra e associe um ingrediente antes da entrada.")
    _pantry_food(db, family.id, item.food_item_id)
    if item.unit is None:
        raise HTTPException(422, "A compra precisa de uma unidade conhecida.")
    try:
        convert_quantity(data.quantity, data.unit.lower(), item.unit)
    except UnsupportedUnitConversionError as exc:
        raise HTTPException(
            422, "Use uma unidade compatível com o ingrediente, sem estimar densidades."
        ) from exc
    confirmation = db.scalar(
        select(RetailIngredientConfirmation).where(
            RetailIngredientConfirmation.food_item_id == item.food_item_id,
            RetailIngredientConfirmation.family_id == family.id,
        )
    )
    if confirmation and not confirmation_current(confirmation):
        raise HTTPException(
            409, "O rótulo ou ingrediente mudou. Reveja o produto antes da entrada."
        )
    lot = PantryStockLot(
        family_id=family.id,
        food_item_id=item.food_item_id,
        stock_key=f"shopping:{item.id}:receipt",
        quantity_available=data.quantity,
        unit=data.unit.lower(),
        location=data.location or None,
        expires_at=data.expires_at,
        observed_at=datetime.now(UTC),
        is_available=True,
        source="shopping_receipt",
        source_reference=str(item.id),
    )
    db.add(lot)
    db.flush()
    item.pantry_receipt = {
        **received,
        "lot_id": str(lot.id),
        "received_at": lot.observed_at.isoformat(),
        "product_selection": item.product_selection,
    }
    item.item_key = f"received:{item.id}"
    item.version += 1
    db.commit()
    return get_shopping_list(db, family)
