"""Persist user-approved ingredient edits with the same data requirements as the base.

Approval records recipe choices, never a nutrition or restriction certification.
"""
import uuid
import unicodedata
from decimal import Decimal

from sqlalchemy import select

from fastapi import HTTPException

from app.models.food_catalog import FoodItem, Recipe, RecipeIngredient
from app.models.recipe_variant import FamilyRecipeVariant
from app.services.dietary_review import require_family
from app.services.recipe_nutrition import build_recipe_composition
from app.services.recipe_variant import read_variant
from app.services.recipe_variant_integrity import load_recipe, recipe_fingerprint



def _norm_text(value):
    return " ".join(
        "".join(ch for ch in unicodedata.normalize("NFKD", value or "")
                if not unicodedata.combining(ch)).casefold().split()
    )


def _norm_number(value):
    return Decimal(str(value)).normalize()


def _edit_signature(data, base):
    """Compare the effective recipe, not generated IDs or display names."""
    by_id = {ingredient.id: ingredient for ingredient in base.ingredients}
    operations = {operation.recipe_ingredient_id: operation for operation in data.operations}
    rows = []
    for ingredient in sorted(base.ingredients, key=lambda row: (row.sort_order, str(row.id))):
        operation = operations.get(ingredient.id)
        identity = (
            ("id", str(operation.replacement_food_item_id))
            if operation and operation.replacement_food_item_id
            else ("name", _norm_text(operation.replacement_name))
            if operation else ("id", str(ingredient.food_item_id))
        )
        rows.append((
            str(ingredient.id), identity,
            _norm_number(operation.quantity if operation else ingredient.quantity),
            _norm_text(operation.unit if operation else ingredient.unit),
            _norm_text((operation.preparation or None) if operation else ingredient.preparation),
        ))
    serving = data.serving_count if data.serving_count is not None else base.serving_count
    return (_norm_number(serving) if serving is not None else None, tuple(rows))


def _stored_edit_signature(row, recipe, base):
    evidence = {str(operation["recipe_ingredient_id"]): operation for operation in row.operations}
    base_ingredients = sorted(base.ingredients, key=lambda i: (i.sort_order, str(i.id)))
    edited_ingredients = sorted(recipe.ingredients, key=lambda i: (i.sort_order, str(i.id)))
    if len(base_ingredients) != len(edited_ingredients):
        return None
    rows = []
    for original, edited in zip(base_ingredients, edited_ingredients, strict=True):
        operation = evidence.get(str(original.id))
        if operation:
            identity = (
                ("name", _norm_text(operation.get("replacement_name")))
                if operation.get("user_declared") else
                ("id", str(operation.get("replacement_food_item_id")))
            )
        else:
            identity = ("id", str(original.food_item_id))
        rows.append((
            str(original.id), identity, _norm_number(edited.quantity),
            _norm_text(edited.unit), _norm_text(edited.preparation),
        ))
    return (
        _norm_number(recipe.serving_count) if recipe.serving_count is not None else None,
        tuple(rows),
    )


def _find_existing_edit(db, family_id, base, data):
    signature = _edit_signature(data, base)
    rows = db.scalars(
        select(FamilyRecipeVariant)
        .where(
            FamilyRecipeVariant.family_id == family_id,
            FamilyRecipeVariant.base_recipe_id == base.id,
            FamilyRecipeVariant.status == "active",
        )
        .order_by(FamilyRecipeVariant.created_at, FamilyRecipeVariant.id)
    )
    for row in rows:
        recipe = load_recipe(db, row.recipe_id)
        if (
            recipe is not None
            and recipe.is_active
            and recipe.source == "family_adaptation"
            and row.base_fingerprint == recipe_fingerprint(base)
            and row.variant_fingerprint == recipe_fingerprint(recipe)
            and _stored_edit_signature(row, recipe, base) == signature
        ):
            return row
    return None


def create_recipe_edit(db, family_id, data):
    require_family(db, family_id)
    base = load_recipe(db, data.base_recipe_id)
    if base is None or base.family_id not in (None, family_id) or not base.is_active:
        raise HTTPException(404, "Base recipe not available in this Family")
    # Lock the base to serialize concurrent edits from the same Family.
    db.scalar(select(Recipe.id).where(Recipe.id == base.id).with_for_update())
    if base.source in ("family_variant", "family_adaptation") or not base.ingredients:
        raise HTTPException(422, "Choose an original recipe with ingredients")
    originals = {ingredient.id: ingredient for ingredient in base.ingredients}
    operations = {operation.recipe_ingredient_id: operation for operation in data.operations}
    if not set(operations) <= set(originals):
        raise HTTPException(422, "An operation does not belong to this recipe")
    # Idempotency: the same accepted substitutions should reuse one family recipe,
    # even if a different UI session supplies a different display name.
    existing = _find_existing_edit(db, family_id, base, data)
    if existing is not None:
        return read_variant(db, existing)
    replacements = {}
    for operation in data.operations:
        original = originals[operation.recipe_ingredient_id]
        if operation.replacement_food_item_id:
            food = db.get(FoodItem, operation.replacement_food_item_id)
            if food is None or food.family_id not in (None, family_id) or not food.is_active:
                raise HTTPException(404, "Replacement ingredient unavailable in this Family")
            if food.id == original.food_item_id:
                raise HTTPException(422, "Choose a different ingredient")
        else:
            # An accepted description is user data, not an inferred catalogue match.
            food = FoodItem(family_id=family_id, catalog_key=f"recipe-edit:{uuid.uuid4()}",
                            name=operation.replacement_name, food_kind="ingredient",
                            source="user_recipe_edit", description="User-approved replacement; composition not supplied.")
            db.add(food)
        replacements[operation.recipe_ingredient_id] = food
    recipe = Recipe(family_id=family_id, recipe_key=f"recipe-edit:{uuid.uuid4()}",
                    name=data.name, description=base.description,
                    suitable_meal_types=base.suitable_meal_types,
                    serving_count=data.serving_count if data.serving_count is not None else base.serving_count,
                    yield_quantity=base.yield_quantity, yield_unit=base.yield_unit,
                    source="family_adaptation", source_reference=str(base.id), is_active=True)
    db.add(recipe)
    evidence = []
    for ingredient in base.ingredients:
        if not ingredient.food_item.is_active or ingredient.food_item.family_id not in (None, family_id):
            raise HTTPException(422, "Base ingredient unavailable")
        operation = operations.get(ingredient.id)
        food = replacements[ingredient.id] if operation else ingredient.food_item
        recipe.ingredients.append(RecipeIngredient(food_item=food,
            quantity=operation.quantity if operation else ingredient.quantity,
            unit=operation.unit if operation else ingredient.unit,
            preparation=(operation.preparation or None) if operation else ingredient.preparation,
            sort_order=ingredient.sort_order))
        if operation:
            evidence.append({**operation.model_dump(mode="json"),
                "replacement_food_item_id": str(food.id) if food.id else None,
                "replacement_name": food.name, "source_name": ingredient.food_item.name,
                "source_food_item_id": str(ingredient.food_item_id),
                "source_quantity": str(ingredient.quantity), "source_unit": ingredient.unit,
                "user_declared": operation.replacement_food_item_id is None})
    db.flush()
    for item in evidence:
        item["replacement_food_item_id"] = str(replacements[uuid.UUID(item["recipe_ingredient_id"])].id)
    build = build_recipe_composition(recipe)
    # Preserve the existing portion basis, never its nutrient values.
    if data.serving_count is None and base.serving_count is None and base.compositions:
        source = base.compositions[-1]
        build.composition.reference_quantity = source.reference_quantity
        build.composition.reference_unit = source.reference_unit
        build.composition.calculation_inputs = {**build.composition.calculation_inputs,
            "inherited_portion_basis": str(source.id),
            **({"serving_count_estimated": source.calculation_inputs["serving_count_estimated"]}
               if "serving_count_estimated" in (source.calculation_inputs or {}) else {})}
    db.flush()
    row = FamilyRecipeVariant(family_id=family_id, base_recipe_id=base.id, recipe_id=recipe.id,
        name=data.name, status="active", operations=evidence,
        base_fingerprint=recipe_fingerprint(base), variant_fingerprint=recipe_fingerprint(recipe),
        activation_evidence={"mode": "recipe_edit", "nutrition_certified": False})
    db.add(row)
    db.commit()
    return read_variant(db, row)
