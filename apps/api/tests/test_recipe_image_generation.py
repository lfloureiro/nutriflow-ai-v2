import uuid
from pathlib import Path

from app.services.recipe_image_generation import (
    existing_image_url,
    generate_recipe_image,
    image_identity,
)


def test_image_identity_is_deterministic_and_recipe_specific():
    recipe_id = uuid.uuid4()
    first = image_identity(recipe_id, "Bifanas com natas", ["Natas", "Porco"])
    assert first == image_identity(recipe_id, "Bifanas com natas", ["Porco", "Natas"])
    assert first != image_identity(recipe_id, "Bifanas com natas", ["Porco", "Leite"])
    assert first != image_identity(uuid.uuid4(), "Bifanas com natas", ["Porco", "Natas"])
    assert first.endswith(".png")
    assert "/" not in first


def test_image_generation_is_optional_and_never_uses_network_without_key(monkeypatch, tmp_path):
    from app.services import recipe_image_generation as media

    monkeypatch.setattr(media.settings, "nutriflow_recipe_image_directory", tmp_path)
    monkeypatch.setattr(media.settings, "nutriflow_recipe_image_generation_enabled", True)
    monkeypatch.setattr(media.settings, "openai_api_key", None)
    recipe_id = uuid.uuid4()
    generate_recipe_image(recipe_id, "Frango com arroz", ["Frango", "Arroz"])
    assert not list(Path(tmp_path).glob("*.png"))
    assert existing_image_url(recipe_id, "Frango com arroz", ["Frango", "Arroz"]) is None


def test_image_url_only_exposes_existing_version(tmp_path, monkeypatch):
    from app.services import recipe_image_generation as media

    monkeypatch.setattr(media.settings, "nutriflow_recipe_image_directory", tmp_path)
    recipe_id = uuid.uuid4()
    name = "Bifanas com natas"
    target = media.image_path(recipe_id, name, ["Porco", "Natas"])
    target.write_bytes(b"placeholder for path identity test")
    url = existing_image_url(recipe_id, name, ["Natas", "Porco"])
    assert url is not None
    assert str(recipe_id) in url
    assert existing_image_url(recipe_id, name, ["Frango"]) is None
