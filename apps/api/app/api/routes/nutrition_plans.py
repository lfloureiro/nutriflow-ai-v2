import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.meal_type import MealType
from app.schemas.nutrition_plan import (
    EffectiveNutritionPlanRead,
    NutritionPlanCreate,
    NutritionPlanDetailRead,
    NutritionPlanGuidelineCreate,
    NutritionPlanGuidelineRead,
    NutritionPlanGuidelineUpdate,
    NutritionPlanRead,
    NutritionPlanRuleCreate,
    NutritionPlanRuleRead,
    NutritionPlanUpdate,
    NutritionPlanVersionCreate,
)
from app.services.nutrition_plan import (
    NutritionPlanError,
    add_nutrition_plan_guideline,
    add_nutrition_plan_rule,
    compile_effective_nutrition_plan,
    create_nutrition_plan,
    create_nutrition_plan_version,
    delete_nutrition_plan,
    delete_nutrition_plan_guideline,
    delete_nutrition_plan_rule,
    get_nutrition_plan,
    list_nutrition_plans,
    update_nutrition_plan,
    update_nutrition_plan_guideline,
)
from app.services.person import get_person

router = APIRouter(prefix="/persons", tags=["nutrition-plans"])


def _require_person(db: Session, person_id: uuid.UUID):
    person = get_person(db, person_id)
    if person is None:
        raise HTTPException(status_code=404, detail="Person not found")
    return person


def _require_plan(db: Session, person_id: uuid.UUID, plan_id: uuid.UUID):
    plan = get_nutrition_plan(db, person_id=person_id, plan_id=plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Nutrition plan not found")
    return plan


@router.get("/{person_id}/nutrition-plans", response_model=list[NutritionPlanRead])
def list_nutrition_plans_endpoint(
    person_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
) -> list[NutritionPlanRead]:
    _require_person(db, person_id)
    return list_nutrition_plans(db, person_id=person_id)


@router.post(
    "/{person_id}/nutrition-plans",
    response_model=NutritionPlanDetailRead,
    status_code=status.HTTP_201_CREATED,
)
def create_nutrition_plan_endpoint(
    person_id: uuid.UUID,
    data: NutritionPlanCreate,
    db: Annotated[Session, Depends(get_db)],
) -> NutritionPlanDetailRead:
    person = _require_person(db, person_id)
    try:
        return create_nutrition_plan(db, person=person, data=data)
    except NutritionPlanError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get(
    "/{person_id}/nutrition-plans/{plan_id}",
    response_model=NutritionPlanDetailRead,
)
def get_nutrition_plan_endpoint(
    person_id: uuid.UUID,
    plan_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
) -> NutritionPlanDetailRead:
    return _require_plan(db, person_id, plan_id)


@router.patch(
    "/{person_id}/nutrition-plans/{plan_id}",
    response_model=NutritionPlanDetailRead,
)
def update_nutrition_plan_endpoint(
    person_id: uuid.UUID,
    plan_id: uuid.UUID,
    data: NutritionPlanUpdate,
    db: Annotated[Session, Depends(get_db)],
) -> NutritionPlanDetailRead:
    plan = _require_plan(db, person_id, plan_id)
    try:
        return update_nutrition_plan(db, plan=plan, data=data)
    except NutritionPlanError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.delete(
    "/{person_id}/nutrition-plans/{plan_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_nutrition_plan_endpoint(
    person_id: uuid.UUID,
    plan_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    plan = _require_plan(db, person_id, plan_id)
    try:
        delete_nutrition_plan(db, plan=plan)
    except NutritionPlanError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{person_id}/nutrition-plans/{plan_id}/versions",
    response_model=NutritionPlanDetailRead,
    status_code=status.HTTP_201_CREATED,
)
def create_nutrition_plan_version_endpoint(
    person_id: uuid.UUID,
    plan_id: uuid.UUID,
    data: NutritionPlanVersionCreate,
    db: Annotated[Session, Depends(get_db)],
) -> NutritionPlanDetailRead:
    plan = _require_plan(db, person_id, plan_id)
    try:
        return create_nutrition_plan_version(db, base_plan=plan, data=data)
    except NutritionPlanError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post(
    "/{person_id}/nutrition-plans/{plan_id}/rules",
    response_model=NutritionPlanRuleRead,
    status_code=status.HTTP_201_CREATED,
)
def add_nutrition_plan_rule_endpoint(
    person_id: uuid.UUID,
    plan_id: uuid.UUID,
    data: NutritionPlanRuleCreate,
    db: Annotated[Session, Depends(get_db)],
) -> NutritionPlanRuleRead:
    plan = _require_plan(db, person_id, plan_id)
    try:
        return add_nutrition_plan_rule(db, plan=plan, data=data)
    except NutritionPlanError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.delete(
    "/{person_id}/nutrition-plans/{plan_id}/rules/{rule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_nutrition_plan_rule_endpoint(
    person_id: uuid.UUID,
    plan_id: uuid.UUID,
    rule_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    plan = _require_plan(db, person_id, plan_id)
    try:
        delete_nutrition_plan_rule(db, plan=plan, rule_id=rule_id)
    except NutritionPlanError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{person_id}/nutrition-plans/{plan_id}/guidelines",
    response_model=NutritionPlanGuidelineRead,
    status_code=status.HTTP_201_CREATED,
)
def add_nutrition_plan_guideline_endpoint(
    person_id: uuid.UUID,
    plan_id: uuid.UUID,
    data: NutritionPlanGuidelineCreate,
    db: Annotated[Session, Depends(get_db)],
) -> NutritionPlanGuidelineRead:
    plan = _require_plan(db, person_id, plan_id)
    try:
        return add_nutrition_plan_guideline(db, plan=plan, data=data)
    except NutritionPlanError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.put(
    "/{person_id}/nutrition-plans/{plan_id}/guidelines/{guideline_id}",
    response_model=NutritionPlanGuidelineRead,
)
def update_nutrition_plan_guideline_endpoint(
    person_id: uuid.UUID,
    plan_id: uuid.UUID,
    guideline_id: uuid.UUID,
    data: NutritionPlanGuidelineUpdate,
    db: Annotated[Session, Depends(get_db)],
) -> NutritionPlanGuidelineRead:
    plan = _require_plan(db, person_id, plan_id)
    try:
        return update_nutrition_plan_guideline(
            db,
            plan=plan,
            guideline_id=guideline_id,
            data=data,
        )
    except NutritionPlanError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.delete(
    "/{person_id}/nutrition-plans/{plan_id}/guidelines/{guideline_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_nutrition_plan_guideline_endpoint(
    person_id: uuid.UUID,
    plan_id: uuid.UUID,
    guideline_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    plan = _require_plan(db, person_id, plan_id)
    try:
        delete_nutrition_plan_guideline(
            db,
            plan=plan,
            guideline_id=guideline_id,
        )
    except NutritionPlanError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/{person_id}/effective-nutrition-plan",
    response_model=EffectiveNutritionPlanRead,
)
def get_effective_nutrition_plan_endpoint(
    person_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    on_date: Annotated[date, Query()],
    meal_type: Annotated[MealType, Query()],
) -> EffectiveNutritionPlanRead:
    try:
        return compile_effective_nutrition_plan(
            db,
            person_id=person_id,
            on_date=on_date,
            meal_type=meal_type,
        )
    except NutritionPlanError as exc:
        if str(exc) == "Person not found.":
            raise HTTPException(status_code=404, detail="Person not found") from exc
        raise HTTPException(status_code=422, detail=str(exc)) from exc
