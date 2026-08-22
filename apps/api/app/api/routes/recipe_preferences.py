import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.recipe_preference import RecipePreferenceSummaryRead, RecipeRatingWrite
from app.services.recipe_preference import (
    RecipePreferenceNotFoundError,
    clear_recipe_rating,
    get_recipe_preference_summary,
    set_recipe_rating,
)

router = APIRouter(
    prefix="/families/{family_id}/recipes/{recipe_id}/preferences",
    tags=["recipe-preferences"],
)


@router.get("", response_model=RecipePreferenceSummaryRead)
def get_recipe_preferences_endpoint(
    family_id: uuid.UUID,
    recipe_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
) -> RecipePreferenceSummaryRead:
    try:
        return get_recipe_preference_summary(db, family_id=family_id, recipe_id=recipe_id)
    except RecipePreferenceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put("/{person_id}", response_model=RecipePreferenceSummaryRead)
def set_recipe_rating_endpoint(
    family_id: uuid.UUID,
    recipe_id: uuid.UUID,
    person_id: uuid.UUID,
    data: RecipeRatingWrite,
    db: Annotated[Session, Depends(get_db)],
) -> RecipePreferenceSummaryRead:
    try:
        return set_recipe_rating(
            db,
            family_id=family_id,
            recipe_id=recipe_id,
            person_id=person_id,
            data=data,
        )
    except RecipePreferenceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/{person_id}", response_model=RecipePreferenceSummaryRead)
def clear_recipe_rating_endpoint(
    family_id: uuid.UUID,
    recipe_id: uuid.UUID,
    person_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
) -> RecipePreferenceSummaryRead:
    try:
        return clear_recipe_rating(
            db,
            family_id=family_id,
            recipe_id=recipe_id,
            person_id=person_id,
        )
    except RecipePreferenceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
