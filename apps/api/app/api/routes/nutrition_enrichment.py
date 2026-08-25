import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.nutrition_enrichment import NutritionEnrichmentRunRead
from app.services.family import get_family
from app.services.nutrition_enrichment_runtime import run_automatic_nutrition_enrichment
from app.services.portfir import PortfirError
from app.services.portfir_enrichment import PortfirEnrichmentError

router = APIRouter(prefix="/families", tags=["nutrition-enrichment"])


@router.post(
    "/{family_id}/nutrition-enrichment/auto",
    response_model=NutritionEnrichmentRunRead,
)
def auto_enrich_family_nutrition_endpoint(
    family_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    refresh: Annotated[bool, Query()] = False,
    limit: Annotated[int, Query(ge=1, le=1000)] = 200,
) -> NutritionEnrichmentRunRead:
    if get_family(db, family_id) is None:
        raise HTTPException(status_code=404, detail="Family not found")

    try:
        result = run_automatic_nutrition_enrichment(
            db,
            refresh=refresh,
            limit=limit,
        )
        db.commit()
        return result
    except PortfirError as exc:
        db.rollback()
        raise HTTPException(
            status_code=503,
            detail="PortFIR nutrition data is temporarily unavailable.",
        ) from exc
    except PortfirEnrichmentError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
