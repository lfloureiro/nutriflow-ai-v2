from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.app_env == "development" and settings.nutriflow_auto_update_local_db:
        # Startup fails rather than serving against an outdated schema.
        from app.local_db_update import apply_local_updates

        apply_local_updates()
    yield


app = FastAPI(
    title=settings.app_name,
    version="2.0.0",
    debug=settings.app_debug,
    lifespan=lifespan,
)

app.include_router(api_router)
