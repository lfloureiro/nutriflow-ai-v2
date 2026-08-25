from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import settings
from app.providers.apify_delivery import (
    GlovoApifyAdapter,
    UberEatsApifyAdapter,
    apify_delivery_configured,
)
from app.providers.registry import register_meal_delivery_adapter


def _register_runtime_providers() -> None:
    if not apify_delivery_configured():
        return
    register_meal_delivery_adapter(UberEatsApifyAdapter())
    register_meal_delivery_adapter(GlovoApifyAdapter())


_register_runtime_providers()

app = FastAPI(
    title=settings.app_name,
    version="2.0.0",
    debug=settings.app_debug,
)

app.include_router(api_router)
