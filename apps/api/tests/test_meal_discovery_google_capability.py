from app.models.family import Family
from app.services import meal_discovery_capability


def _family() -> Family:
    return Family(
        name="Família Teste",
        timezone="Europe/Lisbon",
        restaurant_area="Benfica, Lisboa",
        meal_discovery_sources=["shared_recipes", "restaurants"],
    )


def _restaurants_capability(family: Family):
    result = meal_discovery_capability.build_meal_discovery_capabilities(family)
    return next(item for item in result.capabilities if item.source == "restaurants")


def test_apify_or_direct_google_credentials_enable_google_restaurant_capability(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        meal_discovery_capability,
        "google_restaurant_discovery_configured",
        lambda: True,
    )

    capability = _restaurants_capability(_family())

    assert capability.status == "ready"
    assert capability.live is True
    assert capability.credentials_configured is True
    assert "Google restaurant discovery" in capability.detail


def test_osm_remains_fallback_when_no_google_credentials(monkeypatch) -> None:
    monkeypatch.setattr(
        meal_discovery_capability,
        "google_restaurant_discovery_configured",
        lambda: False,
    )

    capability = _restaurants_capability(_family())

    assert capability.status == "ready"
    assert capability.live is True
    assert capability.credentials_configured is False
    assert "OpenStreetMap fallback" in capability.detail
