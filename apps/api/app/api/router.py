from fastapi import APIRouter

from app.api.routes.families import router as families_router
from app.api.routes.health import router as health_router
from app.api.routes.persons import router as persons_router

api_router = APIRouter(prefix="/api")

api_router.include_router(health_router)
api_router.include_router(families_router)
api_router.include_router(persons_router)
