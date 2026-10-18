import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.nutrition_plan_document import NutritionPlanDocumentExtractionRead
from app.schemas.nutrition_plan_import import (
    NutritionPlanChatGPTImportCreate,
    NutritionPlanChatGPTPromptRead,
    NutritionPlanImportCreate,
    NutritionPlanImportProposalCreate,
    NutritionPlanImportProposalRead,
    NutritionPlanImportProposalUpdate,
    NutritionPlanImportRead,
)
from app.services.nutrition_plan_ai_import import (
    NutritionPlanAIImportError,
    build_chatgpt_nutrition_plan_prompt,
    create_ai_nutrition_plan_import,
    create_chatgpt_assisted_nutrition_plan_import,
)
from app.services.nutrition_plan_document import (
    MAX_DOCUMENT_BYTES,
    NutritionPlanDocumentError,
    extract_nutrition_plan_document,
)
from app.services.nutrition_plan_import import (
    NutritionPlanImportError,
    add_nutrition_plan_import_proposal,
    apply_nutrition_plan_import,
    cancel_nutrition_plan_import,
    create_nutrition_plan_import,
    get_nutrition_plan_import,
    list_nutrition_plan_imports,
    update_nutrition_plan_import_proposal,
)
from app.services.person import get_person

router = APIRouter(prefix="/persons", tags=["nutrition-plan-imports"])


def _require_person(db: Session, person_id: uuid.UUID):
    person = get_person(db, person_id)
    if person is None:
        raise HTTPException(status_code=404, detail="Person not found")
    return person


def _require_import(
    db: Session,
    person_id: uuid.UUID,
    import_id: uuid.UUID,
):
    import_session = get_nutrition_plan_import(
        db,
        person_id=person_id,
        import_id=import_id,
    )
    if import_session is None:
        raise HTTPException(status_code=404, detail="Nutrition plan import not found")
    return import_session


@router.get(
    "/{person_id}/nutrition-plan-imports",
    response_model=list[NutritionPlanImportRead],
)
def list_nutrition_plan_imports_endpoint(
    person_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
) -> list[NutritionPlanImportRead]:
    _require_person(db, person_id)
    return list_nutrition_plan_imports(db, person_id=person_id)


@router.post(
    "/{person_id}/nutrition-plan-imports/extract-document",
    response_model=NutritionPlanDocumentExtractionRead,
)
async def extract_nutrition_plan_document_endpoint(
    person_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    document: Annotated[UploadFile, File()],
) -> NutritionPlanDocumentExtractionRead:
    _require_person(db, person_id)
    data = await document.read(MAX_DOCUMENT_BYTES + 1)
    try:
        return extract_nutrition_plan_document(
            filename=document.filename or "document",
            content_type=document.content_type,
            data=data,
        )
    except NutritionPlanDocumentError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post(
    "/{person_id}/nutrition-plan-imports",
    response_model=NutritionPlanImportRead,
    status_code=status.HTTP_201_CREATED,
)
def create_nutrition_plan_import_endpoint(
    person_id: uuid.UUID,
    data: NutritionPlanImportCreate,
    db: Annotated[Session, Depends(get_db)],
) -> NutritionPlanImportRead:
    person = _require_person(db, person_id)
    try:
        return create_nutrition_plan_import(db, person=person, data=data)
    except NutritionPlanImportError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post(
    "/{person_id}/nutrition-plan-imports/ai",
    response_model=NutritionPlanImportRead,
    status_code=status.HTTP_201_CREATED,
)
def create_ai_nutrition_plan_import_endpoint(
    person_id: uuid.UUID,
    data: NutritionPlanImportCreate,
    db: Annotated[Session, Depends(get_db)],
) -> NutritionPlanImportRead:
    person = _require_person(db, person_id)
    try:
        return create_ai_nutrition_plan_import(db, person=person, data=data)
    except NutritionPlanAIImportError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post(
    "/{person_id}/nutrition-plan-imports/chatgpt/prompt",
    response_model=NutritionPlanChatGPTPromptRead,
)
def create_chatgpt_nutrition_plan_prompt_endpoint(
    person_id: uuid.UUID,
    data: NutritionPlanImportCreate,
    db: Annotated[Session, Depends(get_db)],
) -> NutritionPlanChatGPTPromptRead:
    _require_person(db, person_id)
    return NutritionPlanChatGPTPromptRead(
        prompt=build_chatgpt_nutrition_plan_prompt(data.source_text)
    )


@router.post(
    "/{person_id}/nutrition-plan-imports/chatgpt",
    response_model=NutritionPlanImportRead,
    status_code=status.HTTP_201_CREATED,
)
def create_chatgpt_assisted_nutrition_plan_import_endpoint(
    person_id: uuid.UUID,
    data: NutritionPlanChatGPTImportCreate,
    db: Annotated[Session, Depends(get_db)],
) -> NutritionPlanImportRead:
    person = _require_person(db, person_id)
    try:
        return create_chatgpt_assisted_nutrition_plan_import(
            db,
            person=person,
            data=data.plan,
            response_text=data.response_text,
        )
    except NutritionPlanAIImportError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get(
    "/{person_id}/nutrition-plan-imports/{import_id}",
    response_model=NutritionPlanImportRead,
)
def get_nutrition_plan_import_endpoint(
    person_id: uuid.UUID,
    import_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
) -> NutritionPlanImportRead:
    return _require_import(db, person_id, import_id)


@router.post(
    "/{person_id}/nutrition-plan-imports/{import_id}/proposals",
    response_model=NutritionPlanImportProposalRead,
    status_code=status.HTTP_201_CREATED,
)
def add_nutrition_plan_import_proposal_endpoint(
    person_id: uuid.UUID,
    import_id: uuid.UUID,
    data: NutritionPlanImportProposalCreate,
    db: Annotated[Session, Depends(get_db)],
) -> NutritionPlanImportProposalRead:
    import_session = _require_import(db, person_id, import_id)
    try:
        return add_nutrition_plan_import_proposal(
            db,
            import_session=import_session,
            data=data,
        )
    except NutritionPlanImportError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.patch(
    "/{person_id}/nutrition-plan-imports/{import_id}/proposals/{proposal_id}",
    response_model=NutritionPlanImportProposalRead,
)
def update_nutrition_plan_import_proposal_endpoint(
    person_id: uuid.UUID,
    import_id: uuid.UUID,
    proposal_id: uuid.UUID,
    data: NutritionPlanImportProposalUpdate,
    db: Annotated[Session, Depends(get_db)],
) -> NutritionPlanImportProposalRead:
    import_session = _require_import(db, person_id, import_id)
    try:
        return update_nutrition_plan_import_proposal(
            db,
            import_session=import_session,
            proposal_id=proposal_id,
            data=data,
        )
    except NutritionPlanImportError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post(
    "/{person_id}/nutrition-plan-imports/{import_id}/apply",
    response_model=NutritionPlanImportRead,
)
def apply_nutrition_plan_import_endpoint(
    person_id: uuid.UUID,
    import_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
) -> NutritionPlanImportRead:
    import_session = _require_import(db, person_id, import_id)
    try:
        return apply_nutrition_plan_import(db, import_session=import_session)
    except NutritionPlanImportError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post(
    "/{person_id}/nutrition-plan-imports/{import_id}/cancel",
    response_model=NutritionPlanImportRead,
)
def cancel_nutrition_plan_import_endpoint(
    person_id: uuid.UUID,
    import_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
) -> NutritionPlanImportRead:
    import_session = _require_import(db, person_id, import_id)
    try:
        return cancel_nutrition_plan_import(db, import_session=import_session)
    except NutritionPlanImportError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
