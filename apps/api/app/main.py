from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import settings


app = FastAPI(
    title=settings.app_name,
    version="2.0.0",
    debug=settings.app_debug,
)

app.include_router(api_router)
