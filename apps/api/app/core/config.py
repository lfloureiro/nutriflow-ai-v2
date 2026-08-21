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

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
