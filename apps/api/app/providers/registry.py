from app.providers.meal_delivery import MealDeliveryDiscoveryAdapter


_MEAL_DELIVERY_ADAPTERS: dict[str, MealDeliveryDiscoveryAdapter] = {}


def register_meal_delivery_adapter(adapter: MealDeliveryDiscoveryAdapter) -> None:
    provider_key = adapter.provider_key.strip()
    if not provider_key:
        raise ValueError("Meal delivery adapter provider_key cannot be empty.")
    _MEAL_DELIVERY_ADAPTERS[provider_key] = adapter


def unregister_meal_delivery_adapter(provider_key: str) -> None:
    _MEAL_DELIVERY_ADAPTERS.pop(provider_key, None)


def get_registered_meal_delivery_adapter(
    provider_key: str,
) -> MealDeliveryDiscoveryAdapter | None:
    return _MEAL_DELIVERY_ADAPTERS.get(provider_key)


def has_registered_meal_delivery_adapter(provider_key: str) -> bool:
    return provider_key in _MEAL_DELIVERY_ADAPTERS


def clear_meal_delivery_adapters() -> None:
    _MEAL_DELIVERY_ADAPTERS.clear()
