from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import settings


router = APIRouter(tags=["system"])


class HealthResponse(BaseModel):
    status: str
    application: str
    environment: str


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    return HealthResponse(
        status="ok",
        application=settings.app_name,
        environment=settings.app_env,
    )

