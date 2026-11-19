"""Persist user-approved ingredient edits with the same data requirements as the base.

Approval records recipe choices, never a nutrition or restriction certification.
"""
import uuid

from fastapi import HTTPException

from app.models.food_catalog import FoodItem, Recipe, RecipeIngredient
from app.models.recipe_variant import FamilyRecipeVariant
from app.services.dietary_review import require_family
from app.services.recipe_nutrition import build_recipe_composition
from app.services.recipe_variant import read_variant
from app.services.recipe_variant_integrity import load_recipe, recipe_fingerprint


def create_recipe_edit(db, family_id, data):
    require_family(db, family_id)
    base = load_recipe(db, data.base_recipe_id)
    if base is None or base.family_id not in (None, family_id) or not base.is_active:
        raise HTTPException(404, "Base recipe not available in this Family")
    if base.source in ("family_variant", "family_adaptation") or not base.ingredients:
        raise HTTPException(422, "Choose an original recipe with ingredients")
    originals = {ingredient.id: ingredient for ingredient in base.ingredients}
    operations = {operation.recipe_ingredient_id: operation for operation in data.operations}
    if not set(operations) <= set(originals):
        raise HTTPException(422, "An operation does not belong to this recipe")
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
