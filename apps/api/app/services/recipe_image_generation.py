"""Optional, non-blocking AI food illustrations for newly saved recipes.

A versioned media identity prevents showing a stale photo after a recipe edit.
Only culinary names/ingredients are sent to the configured image provider; no
family member identity or dietary/medical preferences are included.
"""
import base64
import hashlib
import json
import logging
import os
import uuid
from pathlib import Path
from urllib import error, request

from app.core.config import PROJECT_ROOT, settings

logger = logging.getLogger(__name__)


def image_identity(recipe_id, name, ingredient_names):
    recipe_id = uuid.UUID(str(recipe_id))
    payload = json.dumps(
        {"name": name.strip(), "ingredients": sorted(i.strip() for i in ingredient_names)},
        sort_keys=True,
        ensure_ascii=False,
    )
    fingerprint = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
    return f"{recipe_id}-{fingerprint}.png"


def image_root():
    return Path(settings.nutriflow_recipe_image_directory or PROJECT_ROOT / "data" / "recipe-images")


def image_path(recipe_id, name, ingredient_names):
    return image_root() / image_identity(recipe_id, name, ingredient_names)


def existing_image_url(recipe_id, name, ingredient_names):
    file = image_path(recipe_id, name, ingredient_names)
    return (
        f"/api/families/{{family_id}}/recipes/{uuid.UUID(str(recipe_id))}/image"
        if file.is_file() else None
    )


def generate_recipe_image(recipe_id, name, ingredient_names):
    """Synchronous background worker; exceptions never roll back a recipe save."""
    if not settings.nutriflow_recipe_image_generation_enabled or not settings.openai_api_key:
        return
    target = image_path(recipe_id, name, ingredient_names)
    if target.is_file():
        return
    ingredients = ", ".join(ingredient_names[:14]) or "ingredients not specified"
    prompt = (
        "Photorealistic appetizing home-cooked food photograph, single plated dish, "
        "natural warm light, elegant plating, unobtrusive background, three-quarter angle. "
        f"Recipe: {name[:160]}. Ingredients: {ingredients[:750]}. "
        "No text, no writing, no logos, no people. This is an illustration of the recipe "
        "and must not suggest ingredients that are not in the recipe."
    )
    payload = json.dumps({
        "model": settings.nutriflow_recipe_image_model,
        "prompt": prompt,
        "size": "1024x1024",
        "quality": "low",
        "output_format": "png",
    }).encode("utf-8")
    endpoint = settings.openai_base_url.rstrip("/") + "/images/generations"
    req = request.Request(
        endpoint, data=payload,
        headers={
            "Authorization": f"Bearer {settings.openai_api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=160) as response:
            result = json.load(response)
        encoded = result["data"][0]["b64_json"]
        binary = base64.b64decode(encoded, validate=True)
        if not binary.startswith(b"\\x89PNG\\r\\n\\x1a\\n") or len(binary) > 15_000_000:
            raise ValueError("Invalid image response")
        target.parent.mkdir(parents=True, exist_ok=True)
        temp = target.with_name(target.name + f".{uuid.uuid4().hex}.tmp")
        try:
            temp.write_bytes(binary)
            os.replace(temp, target)
        finally:
            temp.unlink(missing_ok=True)
        logger.info("Generated recipe illustration for recipe_id=%s", recipe_id)
    except (OSError, ValueError, KeyError, TypeError, error.HTTPError, error.URLError):
        logger.exception("Could not generate illustration for recipe_id=%s", recipe_id)
