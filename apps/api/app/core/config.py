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
    restaurant_discovery_nominatim_url: str = "https://nominatim.openstreetmap.org"
    restaurant_discovery_overpass_url: str = "https://overpass-api.de/api/interpreter"
    restaurant_discovery_user_agent: str = "NutriFlowAI/0.1 restaurant-discovery"
    restaurant_discovery_timeout_seconds: float = 8.0
    restaurant_discovery_cache_seconds: int = 21600
    restaurant_discovery_max_results: int = 40

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
