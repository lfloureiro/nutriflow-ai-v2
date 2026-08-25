import os
from typing import Protocol

from app.core.config import settings


class ProviderSecretStore(Protocol):
    def get(self, name: str) -> str | None: ...


class EnvironmentProviderSecretStore:
    def get(self, name: str) -> str | None:
        value = os.getenv(name)
        if value is None:
            configured = getattr(settings, name.casefold(), None)
            value = configured if isinstance(configured, str) else None
        if value is None:
            return None
        value = value.strip()
        return value or None


def get_provider_secret_store() -> ProviderSecretStore:
    if settings.provider_secret_backend == "environment":
        return EnvironmentProviderSecretStore()
    raise RuntimeError(
        f"Unsupported provider secret backend: {settings.provider_secret_backend}. "
        "Configure a supported production vault adapter before enabling provider credentials."
    )


def secrets_present(*names: str) -> bool:
    store = get_provider_secret_store()
    return all(store.get(name) is not None for name in names)
