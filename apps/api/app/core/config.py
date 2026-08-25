from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[4]


class Settings(BaseSettings):
    app_name: str = "NutriFlow AI"
    app_env: str = "development"
    app_debug: bool = True

    database_url: str = "postgresql+psycopg://nutriflow:nutriflow_dev@localhost:5432/nutriflow"

    default_locale: str = "pt-PT"
    default_timezone: str = "Europe/Lisbon"

    restaurant_discovery_enabled: bool = True
    restaurant_apify_google_enabled: bool = True
    restaurant_apify_google_url: str = (
        "https://api.apify.com/v2/actors/compass~crawler-google-places/"
        "run-sync-get-dataset-items?maxItems=20&maxTotalChargeUsd=0.05"
    )
    restaurant_apify_timeout_seconds: float = 120.0
    # Direct Google Places is intentionally disabled by default: NutriFlow must not require
    # billing-enabled APIs for normal operation.
    restaurant_google_places_enabled: bool = False
    restaurant_google_places_url: str = "https://places.googleapis.com/v1/places:searchText"
    restaurant_discovery_nominatim_url: str = "https://nominatim.openstreetmap.org"
    restaurant_discovery_overpass_url: str = "https://overpass-api.de/api/interpreter"
    restaurant_discovery_user_agent: str = "NutriFlowAI/0.1 restaurant-discovery"
    restaurant_discovery_timeout_seconds: float = 8.0
    restaurant_discovery_cache_seconds: int = 21600
    restaurant_discovery_max_results: int = 20

    provider_secret_backend: str = "environment"
    nutriflow_apify_api_token: str | None = None
    nutriflow_google_places_api_key: str | None = None
    nutriflow_fdc_api_key: str | None = None
    nutriflow_uber_client_id: str | None = None
    nutriflow_uber_client_secret: str | None = None
    nutriflow_glovo_client_id: str | None = None
    nutriflow_glovo_client_secret: str | None = None
    nutriflow_bolt_food_integrator_id: str | None = None
    nutriflow_bolt_food_secret_key: str | None = None
    uber_consumer_delivery_enabled: bool = False
    glovo_consumer_discovery_enabled: bool = False
    bolt_food_consumer_discovery_enabled: bool = False

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
