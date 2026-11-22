import uuid
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.recipe_variant import (
    RecipeEditCreate,
    VariantCreate,
    VariantRead,
    VariantRetireRequest,
    VariantValidationRead,
    VariantValidationRequest,
)
from app.services.recipe_duplicate_audit import duplicate_family_adaptations
from app.services.recipe_image_generation import generate_recipe_image
from app.services.recipe_variant import (
    activate_variant,
    create_variant,
    list_variants,
    retire_variant,
    validate_variant,
)

router = APIRouter(prefix="/families/{family_id}/recipe-variants", tags=["recipe variants"])
DB = Annotated[Session, Depends(get_db)]


@router.get("/duplicates")
def duplicate_family_adaptations_endpoint(family_id: uuid.UUID, db: DB):
    return duplicate_family_adaptations(db, family_id)


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


@router.post("/recipe-edit", response_model=VariantRead, status_code=201)
def create_recipe_edit_endpoint(
    family_id: uuid.UUID, data: RecipeEditCreate, background_tasks: BackgroundTasks, db: DB
):
    from app.services.recipe_edit import create_recipe_edit
    from app.services.recipe_variant_integrity import load_recipe

    result = create_recipe_edit(db, family_id, data)
    recipe = load_recipe(db, result.recipe_id)
    if recipe is not None:
        background_tasks.add_task(
            generate_recipe_image, recipe.id, recipe.name,
            [ingredient.food_item.name for ingredient in recipe.ingredients],
        )
    return result
