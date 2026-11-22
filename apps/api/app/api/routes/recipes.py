import uuid
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Response, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.recipe_catalogue import RecipeCreate, RecipeRead, RecipeUpdate
from app.services.family import get_family
from app.services.recipe_catalogue import (
    RecipeCatalogueError,
    RecipeIngredientError,
    RecipeNotFoundError,
    create_family_recipe,
    deactivate_family_recipe,
    get_family_recipe,
    get_family_recipe_model,
    list_family_recipes,
    update_family_recipe,
)
from app.services.recipe_image_generation import generate_recipe_image, image_path

router = APIRouter(prefix="/families/{family_id}/recipes", tags=["recipes"])


def _require_family(db: Session, family_id: uuid.UUID):
    family = get_family(db, family_id)
    if family is None:
        raise HTTPException(status_code=404, detail="Family not found")
    return family


@router.get("", response_model=list[RecipeRead])
def list_family_recipes_endpoint(
    family_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    q: Annotated[str | None, Query(max_length=160)] = None,
    include_inactive: bool = False,
) -> list[RecipeRead]:
    _require_family(db, family_id)
    return list_family_recipes(
        db,
        family_id,
        query=q,
        include_inactive=include_inactive,
    )


@router.post("", response_model=RecipeRead, status_code=status.HTTP_201_CREATED)
def create_family_recipe_endpoint(
    family_id: uuid.UUID,
    data: RecipeCreate,
    background_tasks: BackgroundTasks,
    db: Annotated[Session, Depends(get_db)],
) -> RecipeRead:
    family = _require_family(db, family_id)
    try:
        result = create_family_recipe(db, family, data)
        background_tasks.add_task(
            generate_recipe_image, result.id, result.name,
            [ingredient.food_item_name for ingredient in result.ingredients],
        )
        return result
    except (RecipeCatalogueError, RecipeIngredientError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/{recipe_id}", response_model=RecipeRead)
def get_family_recipe_endpoint(
    family_id: uuid.UUID,
    recipe_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
) -> RecipeRead:
    _require_family(db, family_id)
    recipe = get_family_recipe(db, family_id, recipe_id)
    if recipe is None:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return recipe


@router.patch("/{recipe_id}", response_model=RecipeRead)
def update_family_recipe_endpoint(
    family_id: uuid.UUID,
    recipe_id: uuid.UUID,
    data: RecipeUpdate,
    background_tasks: BackgroundTasks,
    db: Annotated[Session, Depends(get_db)],
) -> RecipeRead:
    _require_family(db, family_id)
    try:
        result = update_family_recipe(db, family_id, recipe_id, data)
        if {"name", "ingredients"} & data.model_fields_set:
            background_tasks.add_task(
                generate_recipe_image, result.id, result.name,
                [ingredient.food_item_name for ingredient in result.ingredients],
            )
        return result
    except RecipeNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (RecipeCatalogueError, RecipeIngredientError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/{recipe_id}/image")
def get_generated_recipe_image(
    family_id: uuid.UUID,
    recipe_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
):
    _require_family(db, family_id)
    try:
        recipe = get_family_recipe_model(db, family_id, recipe_id)
    except RecipeNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if recipe.family_id != family_id:
        raise HTTPException(404, "Generated illustration unavailable for shared recipe")
    file = image_path(
        recipe.id, recipe.name, [ingredient.food_item.name for ingredient in recipe.ingredients]
    )
    if not file.is_file():
        raise HTTPException(404, "Recipe illustration not generated yet")
    return FileResponse(file, media_type="image/png")


@router.delete("/{recipe_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_family_recipe_endpoint(
    family_id: uuid.UUID,
    recipe_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    _require_family(db, family_id)
    try:
        deactivate_family_recipe(db, family_id, recipe_id)
    except RecipeNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RecipeCatalogueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
