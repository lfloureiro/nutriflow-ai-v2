import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.recipe_variant import (
    VariantCreate,
    VariantRead,
    VariantRetireRequest,
    VariantValidationRead,
    VariantValidationRequest,
)
from app.services.recipe_variant import (
    activate_variant,
    create_variant,
    list_variants,
    retire_variant,
    validate_variant,
)

router = APIRouter(prefix="/families/{family_id}/recipe-variants", tags=["recipe variants"])
DB = Annotated[Session, Depends(get_db)]


@router.get("", response_model=list[VariantRead])
def list_endpoint(family_id: uuid.UUID, db: DB, base_recipe_id: uuid.UUID | None = None):
    return list_variants(db, family_id, base_recipe_id)


@router.post("", response_model=VariantRead, status_code=201)
def create_endpoint(family_id: uuid.UUID, data: VariantCreate, db: DB):
    return create_variant(db, family_id, data)


@router.post("/{variant_id}/validate", response_model=VariantValidationRead)
def validate_endpoint(
    family_id: uuid.UUID, variant_id: uuid.UUID, data: VariantValidationRequest, db: DB
):
    return validate_variant(db, family_id, variant_id, data)


@router.post("/{variant_id}/activate", response_model=VariantRead)
def activate_endpoint(
    family_id: uuid.UUID, variant_id: uuid.UUID, data: VariantValidationRequest, db: DB
):
    return activate_variant(db, family_id, variant_id, data)


@router.post("/{variant_id}/retire", response_model=VariantRead)
def retire_endpoint(
    family_id: uuid.UUID, variant_id: uuid.UUID, data: VariantRetireRequest, db: DB
):
    return retire_variant(db, family_id, variant_id, data)
