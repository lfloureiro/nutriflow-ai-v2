from fastapi import APIRouter

from app.api.routes.families import router as families_router
from app.api.routes.health import router as health_router
from app.api.routes.ingredients import router as ingredients_router
from app.api.routes.meal_recommendations import router as meal_recommendations_router
from app.api.routes.persons import router as persons_router
from app.api.routes.planning_bootstrap import router as planning_bootstrap_router
from app.api.routes.practical_meal_recommendations import (
    router as practical_meal_recommendations_router,
)
from app.api.routes.recommendation_decisions import router as recommendation_decisions_router

api_router = APIRouter(prefix="/api")

api_router.include_router(health_router)
api_router.include_router(families_router)
api_router.include_router(ingredients_router)
api_router.include_router(persons_router)
api_router.include_router(planning_bootstrap_router)
api_router.include_router(meal_recommendations_router)
api_router.include_router(practical_meal_recommendations_router)
api_router.include_router(recommendation_decisions_router)
