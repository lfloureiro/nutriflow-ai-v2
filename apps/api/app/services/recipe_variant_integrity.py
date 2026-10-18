import hashlib
import json
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.food_catalog import FoodCompositionSnapshot, FoodItem, Recipe, RecipeIngredient
from app.models.recipe_variant import FamilyRecipeVariant


def load_recipe(db, recipe_id):
    return db.scalar(
        select(Recipe)
        .where(Recipe.id == recipe_id)
        .options(
            selectinload(Recipe.ingredients)
            .selectinload(RecipeIngredient.food_item)
            .selectinload(FoodItem.compositions)
            .selectinload(FoodCompositionSnapshot.nutrients),
            selectinload(Recipe.compositions),
        )
    )


def recipe_fingerprint(recipe):
    def number(value):
        return format(Decimal(str(value)).normalize(), "f") if value is not None else None

    payload = {
        "id": str(recipe.id),
        "name": recipe.name,
        "description": recipe.description,
        "servings": number(recipe.serving_count),
        "yield": number(recipe.yield_quantity),
        "yield_unit": recipe.yield_unit,
        "meal_types": recipe.suitable_meal_types,
        "composition": str(recipe.compositions[-1].id) if recipe.compositions else None,
        "ingredients": [
            {
                "id": str(i.id),
                "food": str(i.food_item_id),
                "quantity": number(i.quantity),
                "unit": i.unit,
                "preparation": i.preparation,
                "order": i.sort_order,
                "food_active": i.food_item.is_active,
                "composition": str(i.food_item.compositions[-1].id)
                if i.food_item.compositions
                else None,
            }
            for i in recipe.ingredients
        ],
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def variant_issues(db, row):
    base = load_recipe(db, row.base_recipe_id)
    recipe = load_recipe(db, row.recipe_id)
    issues = []
    if base is None or not base.is_active or recipe_fingerprint(base) != row.base_fingerprint:
        issues.append("base_recipe_changed: criar uma nova revisão da variante")
    if recipe is None or recipe_fingerprint(recipe) != row.variant_fingerprint:
        issues.append("variant_evidence_changed: ingredientes, receita ou rótulo mudaram")
    if recipe is None or not recipe.compositions:
        issues.append("nutrition_composition_missing")
    else:
        composition = recipe.compositions[-1]
        for ingredient in recipe.ingredients:
            if not ingredient.food_item.is_active or ingredient.food_item.family_id not in (
                None,
                row.family_id,
            ):
                issues.append("ingredient_unavailable")
        issues.extend((composition.calculation_inputs or {}).get("issues", []))
        if composition.energy_kcal is None:
            issues.append("nutrition_energy_missing")
    return issues


def variant_for_recipe(db, recipe_id):
    return db.scalar(select(FamilyRecipeVariant).where(FamilyRecipeVariant.recipe_id == recipe_id))


def assert_variant_usable(db, recipe):
    if recipe.source != "family_variant":
        return
    row = variant_for_recipe(db, recipe.id)
    if row is None or row.status != "active" or not recipe.is_active:
        raise ValueError("Recipe variant is not active")
    issues = variant_issues(db, row)
    if issues:
        raise ValueError("Recipe variant needs revalidation: " + "; ".join(issues))
