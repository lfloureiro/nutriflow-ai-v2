import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.family import Family
from app.schemas.ingredient_catalogue import (
    IngredientCreate,
    IngredientRead,
    IngredientUpdate,
)
from app.services.family import get_family
from app.services.ingredient_catalogue import (
    IngredientNotFoundError,
    create_family_ingredient,
    deactivate_family_ingredient,
    get_family_ingredient,
    list_family_ingredients,
    update_family_ingredient,
)

router = APIRouter(prefix="/families/{family_id}/ingredients", tags=["ingredients"])


def _require_family(db: Session, family_id: uuid.UUID) -> Family:
    family = get_family(db, family_id)
    if family is None:
        raise HTTPException(status_code=404, detail="Family not found")
    return family


@router.get("", response_model=list[IngredientRead])
def list_family_ingredients_endpoint(
    family_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    q: Annotated[str | None, Query(max_length=160)] = None,
    include_inactive: bool = False,
) -> list[IngredientRead]:
    _require_family(db, family_id)
    return list_family_ingredients(
        db,
        family_id,
        query=q,
        include_inactive=include_inactive,
    )


@router.post("", response_model=IngredientRead, status_code=status.HTTP_201_CREATED)
def create_family_ingredient_endpoint(
    family_id: uuid.UUID,
    data: IngredientCreate,
    db: Annotated[Session, Depends(get_db)],
) -> IngredientRead:
    family = _require_family(db, family_id)
    return create_family_ingredient(db, family, data)


@router.get("/{ingredient_id}", response_model=IngredientRead)
def get_family_ingredient_endpoint(
    family_id: uuid.UUID,
    ingredient_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
) -> IngredientRead:
    _require_family(db, family_id)
    ingredient = get_family_ingredient(db, family_id, ingredient_id)
    if ingredient is None:
        raise HTTPException(status_code=404, detail="Ingredient not found")
    return ingredient


@router.patch("/{ingredient_id}", response_model=IngredientRead)
def update_family_ingredient_endpoint(
    family_id: uuid.UUID,
    ingredient_id: uuid.UUID,
    data: IngredientUpdate,
    db: Annotated[Session, Depends(get_db)],
) -> IngredientRead:
    _require_family(db, family_id)
    try:
        return update_family_ingredient(db, family_id, ingredient_id, data)
    except IngredientNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/{ingredient_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_family_ingredient_endpoint(
    family_id: uuid.UUID,
    ingredient_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    _require_family(db, family_id)
    try:
        deactivate_family_ingredient(db, family_id, ingredient_id)
    except IngredientNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
