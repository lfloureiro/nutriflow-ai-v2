import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.family import Family
from app.schemas.pantry_shopping import (
    PantryLotCreate,
    PantryLotRead,
    PantryLotUpdate,
    ShoppingListItemCreate,
    ShoppingListItemUpdate,
    ShoppingListRead,
    ShoppingListRefreshRequest,
)
from app.services.family import get_family
from app.services.pantry_shopping import (
    PantryLotNotFoundError,
    PantryShoppingError,
    ShoppingListItemNotFoundError,
    add_manual_shopping_item,
    create_pantry_lot,
    deactivate_pantry_lot,
    delete_shopping_item,
    get_shopping_list,
    list_pantry_lots,
    refresh_shopping_list,
    update_pantry_lot,
    update_shopping_item,
)

router = APIRouter(prefix="/families/{family_id}", tags=["pantry-shopping"])


def _require_family(db: Session, family_id: uuid.UUID) -> Family:
    family = get_family(db, family_id)
    if family is None:
        raise HTTPException(status_code=404, detail="Family not found")
    return family


def _unprocessable(exc: PantryShoppingError) -> HTTPException:
    return HTTPException(status_code=422, detail=str(exc))


@router.get("/pantry", response_model=list[PantryLotRead])
def list_pantry_endpoint(
    family_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    include_inactive: bool = False,
) -> list[PantryLotRead]:
    _require_family(db, family_id)
    return list_pantry_lots(db, family_id, include_inactive=include_inactive)


@router.post("/pantry", response_model=PantryLotRead, status_code=status.HTTP_201_CREATED)
def create_pantry_endpoint(
    family_id: uuid.UUID,
    data: PantryLotCreate,
    db: Annotated[Session, Depends(get_db)],
) -> PantryLotRead:
    family = _require_family(db, family_id)
    try:
        return create_pantry_lot(db, family, data)
    except PantryShoppingError as exc:
        raise _unprocessable(exc) from exc


@router.patch("/pantry/{lot_id}", response_model=PantryLotRead)
def update_pantry_endpoint(
    family_id: uuid.UUID,
    lot_id: uuid.UUID,
    data: PantryLotUpdate,
    db: Annotated[Session, Depends(get_db)],
) -> PantryLotRead:
    _require_family(db, family_id)
    try:
        return update_pantry_lot(db, family_id, lot_id, data)
    except PantryLotNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PantryShoppingError as exc:
        raise _unprocessable(exc) from exc


@router.delete("/pantry/{lot_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_pantry_endpoint(
    family_id: uuid.UUID,
    lot_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    _require_family(db, family_id)
    try:
        deactivate_pantry_lot(db, family_id, lot_id)
    except PantryLotNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/shopping-list", response_model=ShoppingListRead)
def get_shopping_list_endpoint(
    family_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
) -> ShoppingListRead:
    family = _require_family(db, family_id)
    try:
        return get_shopping_list(db, family)
    except PantryShoppingError as exc:
        raise _unprocessable(exc) from exc


@router.post("/shopping-list/refresh", response_model=ShoppingListRead)
def refresh_shopping_list_endpoint(
    family_id: uuid.UUID,
    data: ShoppingListRefreshRequest,
    db: Annotated[Session, Depends(get_db)],
) -> ShoppingListRead:
    family = _require_family(db, family_id)
    try:
        return refresh_shopping_list(
            db,
            family,
            start_date=data.start_date,
            days=data.days,
        )
    except PantryShoppingError as exc:
        raise _unprocessable(exc) from exc


@router.post(
    "/shopping-list/items",
    response_model=ShoppingListRead,
    status_code=status.HTTP_201_CREATED,
)
def add_manual_shopping_item_endpoint(
    family_id: uuid.UUID,
    data: ShoppingListItemCreate,
    db: Annotated[Session, Depends(get_db)],
) -> ShoppingListRead:
    family = _require_family(db, family_id)
    return add_manual_shopping_item(db, family, data)


@router.patch("/shopping-list/items/{item_id}", response_model=ShoppingListRead)
def update_shopping_item_endpoint(
    family_id: uuid.UUID,
    item_id: uuid.UUID,
    data: ShoppingListItemUpdate,
    db: Annotated[Session, Depends(get_db)],
) -> ShoppingListRead:
    family = _require_family(db, family_id)
    try:
        return update_shopping_item(db, family, item_id, data)
    except ShoppingListItemNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/shopping-list/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_shopping_item_endpoint(
    family_id: uuid.UUID,
    item_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    _require_family(db, family_id)
    try:
        delete_shopping_item(db, family_id, item_id)
    except ShoppingListItemNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
