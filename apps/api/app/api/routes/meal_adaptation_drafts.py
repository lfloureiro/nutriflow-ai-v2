import uuid
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.food_catalog import FoodItem
from app.models.meal import MealEvent
from app.models.meal_adaptation_draft import MealAdaptationDraft
from app.schemas.meal_adaptation_draft import (
    AdaptationDraftRead,
    AdaptationDraftUpdate,
    AdaptationDraftWrite,
)
from app.services.dietary_review import require_family, require_person
from app.services.recipe_variant_integrity import load_recipe, recipe_fingerprint

router = APIRouter(prefix="/families/{family_id}/meal-adaptation-drafts", tags=["adaptation drafts"])
DB = Annotated[Session, Depends(get_db)]


def check_snapshot(db, family_id, data):
    require_family(db, family_id)
    recipe = load_recipe(db, data.base_recipe_id)
    if recipe is None or recipe.family_id not in (None, family_id) or recipe.source == "family_variant":
        raise HTTPException(404, "Original recipe not available in this family")
    ingredient_ids = {ingredient.id for ingredient in recipe.ingredients}
    if not ({op.recipe_ingredient_id for op in data.operations} | set(data.decisions)) <= ingredient_ids:
        raise HTTPException(422, "Draft ingredient does not belong to the original recipe")
    for participant in data.participants:
        require_person(db, family_id, participant.person_id)
    for op in data.operations:
        if op.replacement_food_item_id is not None:
            food = db.get(FoodItem, op.replacement_food_item_id)
            if food is None or food.family_id not in (None, family_id):
                raise HTTPException(404, "Draft replacement not available in this family")
    if data.meal_event_id:
        event = db.get(MealEvent, data.meal_event_id)
        if event is None or event.family_id != family_id:
            raise HTTPException(404, "Meal not available in this family")
        if event.scheduled_at.astimezone(ZoneInfo(event.timezone)).date() != data.planning_date or event.meal_type != data.meal_type:
            raise HTTPException(409, "Meal context changed; reload before saving a draft")
    return recipe


def read_draft(db, row):
    recipe = load_recipe(db, row.base_recipe_id)
    return AdaptationDraftRead(id=row.id, version=row.version, base_changed=recipe is None or recipe_fingerprint(recipe) != row.base_fingerprint, snapshot=row.snapshot, updated_at=row.updated_at)


@router.get("", response_model=list[AdaptationDraftRead])
def list_drafts(family_id: uuid.UUID, db: DB, base_recipe_id: uuid.UUID):
    require_family(db, family_id)
    rows = db.scalars(select(MealAdaptationDraft).where(MealAdaptationDraft.family_id == family_id, MealAdaptationDraft.base_recipe_id == base_recipe_id).order_by(MealAdaptationDraft.updated_at.desc()).limit(30))
    return [read_draft(db, row) for row in rows]


@router.post("", response_model=AdaptationDraftRead, status_code=201)
def save_draft(family_id: uuid.UUID, data: AdaptationDraftWrite, db: DB):
    recipe = check_snapshot(db, family_id, data)
    row = MealAdaptationDraft(family_id=family_id, base_recipe_id=recipe.id, meal_event_id=data.meal_event_id, base_fingerprint=recipe_fingerprint(recipe), snapshot=data.model_dump(mode="json"))
    db.add(row)
    db.commit()
    db.refresh(row)
    return read_draft(db, row)


@router.put("/{draft_id}", response_model=AdaptationDraftRead)
def update_draft(family_id: uuid.UUID, draft_id: uuid.UUID, data: AdaptationDraftUpdate, db: DB):
    row = db.scalar(select(MealAdaptationDraft).where(MealAdaptationDraft.id == draft_id, MealAdaptationDraft.family_id == family_id).with_for_update())
    if row is None:
        raise HTTPException(404, "Draft not available in this family")
    if row.version != data.expected_version or row.base_recipe_id != data.base_recipe_id:
        raise HTTPException(409, "Draft changed; reload before saving")
    recipe = check_snapshot(db, family_id, data)
    row.snapshot = data.model_dump(mode="json", exclude={"expected_version"})
    row.base_fingerprint = recipe_fingerprint(recipe)
    row.meal_event_id = data.meal_event_id
    row.version += 1
    db.commit()
    db.refresh(row)
    return read_draft(db, row)
