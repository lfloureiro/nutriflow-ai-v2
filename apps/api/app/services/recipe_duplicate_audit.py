"""Read-only inventory of family adaptations with identical full compositions."""
from collections import defaultdict

from sqlalchemy import select

from app.models.recipe_variant import FamilyRecipeVariant
from app.services.dietary_review import require_family
from app.services.recipe_edit import _stored_edit_signature
from app.services.recipe_variant_integrity import load_recipe


def duplicate_family_adaptations(db, family_id):
    require_family(db, family_id)
    rows = db.scalars(
        select(FamilyRecipeVariant)
        .where(
            FamilyRecipeVariant.family_id == family_id,
            FamilyRecipeVariant.status == "active",
        )
        .order_by(FamilyRecipeVariant.created_at, FamilyRecipeVariant.id)
    )
    groups = defaultdict(list)
    for row in rows:
        recipe = load_recipe(db, row.recipe_id)
        base = load_recipe(db, row.base_recipe_id)
        if recipe is None or base is None or not recipe.is_active:
            continue
        if recipe.source != "family_adaptation":
            continue
        key = _stored_edit_signature(row, recipe, base)
        if key is not None:
            groups[(row.base_recipe_id, key)].append((row, recipe))
    return [
        {
            "base_recipe_id": str(base_id),
            "recipes": [
                {"variant_id": str(row.id), "recipe_id": str(recipe.id), "name": recipe.name}
                for row, recipe in variants
            ],
            "count": len(variants),
            "action": "manual_review_required",
        }
        for (base_id, _), variants in groups.items()
        if len(variants) > 1
    ]
