from fastapi import APIRouter

from app.api.routes.families import router as families_router
from app.api.routes.health import router as health_router
from app.api.routes.ingredients import router as ingredients_router
from app.api.routes.meal_discovery import router as meal_discovery_router
from app.api.routes.meal_plan import router as meal_plan_router
from app.api.routes.meal_recommendations import router as meal_recommendations_router
from app.api.routes.nutrition_enrichment import router as nutrition_enrichment_router
from app.api.routes.pantry_shopping import router as pantry_shopping_router
from app.api.routes.persons import router as persons_router
from app.api.routes.planning_bootstrap import router as planning_bootstrap_router
from app.api.routes.practical_meal_recommendations import (
    router as practical_meal_recommendations_router,
)
from app.api.routes.recipe_preferences import router as recipe_preferences_router
from app.api.routes.recipes import router as recipes_router
from app.api.routes.recommendation_decisions import router as recommendation_decisions_router
from app.api.routes.restaurant_discovery import router as restaurant_discovery_router
from app.api.routes.shared_practical_recommendations import (
    router as shared_practical_recommendations_router,
)

api_router = APIRouter(prefix="/api")

api_router.include_router(health_router)
api_router.include_router(families_router)
api_router.include_router(ingredients_router)
api_router.include_router(recipes_router)
api_router.include_router(recipe_preferences_router)
api_router.include_router(meal_plan_router)
api_router.include_router(pantry_shopping_router)
api_router.include_router(persons_router)
api_router.include_router(planning_bootstrap_router)
api_router.include_router(meal_recommendations_router)
api_router.include_router(practical_meal_recommendations_router)
api_router.include_router(shared_practical_recommendations_router)
api_router.include_router(recommendation_decisions_router)
api_router.include_router(meal_discovery_router)
api_router.include_router(restaurant_discovery_router)
api_router.include_router(nutrition_enrichment_router)
