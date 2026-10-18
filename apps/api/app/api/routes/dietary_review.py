import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.dietary_review import (
    FodmapReference,
    PersonHealthCondition,
    PersonHealthConditionEvent,
)
from app.schemas.dietary_review import (
    ConditionEventRead,
    ConditionRead,
    ConditionUpdate,
    ConditionWrite,
    FodmapReferenceRead,
    ReviewRecipeRead,
    SubstitutionRead,
    SubstitutionUpdate,
    SubstitutionWrite,
)
from app.services.dietary_review import (
    create_substitution,
    get_condition,
    recipe_reviews,
    require_family,
    require_person,
    review_substitution,
    save_condition,
)

router = APIRouter(tags=["health conditions and dietary review"])
DB = Annotated[Session, Depends(get_db)]
CONDITIONS = "/families/{family_id}/persons/{person_id}/conditions"


@router.get(CONDITIONS, response_model=list[ConditionRead])
def list_conditions(family_id: uuid.UUID, person_id: uuid.UUID, db: DB):
    require_person(db, family_id, person_id)
    return db.scalars(
        select(PersonHealthCondition)
        .where(
            PersonHealthCondition.person_id == person_id,
        )
        .order_by(PersonHealthCondition.created_at)
    ).all()


@router.post(CONDITIONS, response_model=ConditionRead, status_code=201)
def add_condition(family_id: uuid.UUID, person_id: uuid.UUID, data: ConditionWrite, db: DB):
    return save_condition(db, family_id, person_id, data)


@router.put(CONDITIONS + "/{condition_id}", response_model=ConditionRead)
def revise_condition(
    family_id: uuid.UUID,
    person_id: uuid.UUID,
    condition_id: uuid.UUID,
    data: ConditionUpdate,
    db: DB,
):
    return save_condition(db, family_id, person_id, data, condition_id)


@router.get(CONDITIONS + "/{condition_id}/history", response_model=list[ConditionEventRead])
def condition_history(
    family_id: uuid.UUID,
    person_id: uuid.UUID,
    condition_id: uuid.UUID,
    db: DB,
):
    get_condition(db, family_id, person_id, condition_id)
    return db.scalars(
        select(PersonHealthConditionEvent)
        .where(
            PersonHealthConditionEvent.condition_id == condition_id,
        )
        .order_by(PersonHealthConditionEvent.version.desc())
    ).all()


@router.get("/families/{family_id}/fodmap-references", response_model=list[FodmapReferenceRead])
def list_fodmap_references(family_id: uuid.UUID, db: DB):
    require_family(db, family_id)
    return db.scalars(select(FodmapReference).order_by(FodmapReference.name_pt)).all()


@router.get("/families/{family_id}/recipe-adaptations", response_model=list[ReviewRecipeRead])
def list_recipe_adaptations(family_id: uuid.UUID, db: DB):
    return recipe_reviews(db, family_id)


@router.post(
    "/families/{family_id}/recipe-adaptations", response_model=SubstitutionRead, status_code=201
)
def add_recipe_adaptation(family_id: uuid.UUID, data: SubstitutionWrite, db: DB):
    return create_substitution(db, family_id, data)


@router.put(
    "/families/{family_id}/recipe-adaptations/{proposal_id}", response_model=SubstitutionRead
)
def revise_recipe_adaptation(
    family_id: uuid.UUID,
    proposal_id: uuid.UUID,
    data: SubstitutionUpdate,
    db: DB,
):
    return review_substitution(db, family_id, proposal_id, data)
