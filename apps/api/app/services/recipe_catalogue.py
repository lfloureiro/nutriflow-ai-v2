import uuid
from decimal import Decimal

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.family import Family
from app.models.food_catalog import (
    FoodCompositionSnapshot,
    FoodItem,
    Recipe,
    RecipeCompositionSnapshot,
    RecipeIngredient,
)
from app.schemas.recipe_catalogue import (
    RecipeCompositionRead,
    RecipeCreate,
    RecipeIngredientRead,
    RecipeIngredientWrite,
    RecipeNutrientRead,
    RecipeNutritionEvidence,
    RecipeRead,
    RecipeUpdate,
)
from app.services.meal_suitability import recipe_default_meal_types
from app.services.recipe_nutrition import CALCULATION_VERSION as RECIPE_CALCULATION_VERSION
from app.services.recipe_nutrition import build_recipe_composition


class RecipeCatalogueError(ValueError):
    pass


class RecipeNotFoundError(RecipeCatalogueError):
    pass


class RecipeIngredientError(RecipeCatalogueError):
    pass


def _optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


def _recipe_options():
    return (
        selectinload(Recipe.ingredients)
        .selectinload(RecipeIngredient.food_item)
        .selectinload(FoodItem.compositions)
        .selectinload(FoodCompositionSnapshot.nutrients),
        selectinload(Recipe.compositions).selectinload(RecipeCompositionSnapshot.nutrients),
    )


def _latest_composition(recipe: Recipe) -> RecipeCompositionSnapshot | None:
    return recipe.compositions[-1] if recipe.compositions else None


def _calculation_inputs(
    composition: RecipeCompositionSnapshot | None,
) -> dict[str, object]:
    if composition is None or not isinstance(composition.calculation_inputs, dict):
        return {}
    return composition.calculation_inputs


def _composition_issues(composition: RecipeCompositionSnapshot | None) -> list[str]:
    raw = _calculation_inputs(composition).get("issues")
    if not isinstance(raw, list):
        return []
    return [str(item) for item in raw]


def _composition_evidence(
    composition: RecipeCompositionSnapshot,
) -> RecipeNutritionEvidence:
    inputs = _calculation_inputs(composition)
    if inputs.get("nutrition_source") == "synthetic-development-fixture":
        return "synthetic_development"
    if composition.calculation_version.startswith("legacy-v1-demo-synthetic-nutrition"):
        return "synthetic_development"
    if composition.calculation_version == RECIPE_CALCULATION_VERSION:
        if inputs.get("energy_estimated") is True:
            return "ingredient_estimated"
        return "ingredient_calculated"
    if composition.energy_kcal is not None:
        return "imported"
    return "unknown"


def _practical_profile_payload(
    composition: RecipeCompositionSnapshot,
) -> dict[str, object] | None:
    raw = _calculation_inputs(composition).get("practical_profile")
    return raw if isinstance(raw, dict) else None


def _energy_confidence(composition: RecipeCompositionSnapshot) -> str | None:
    if composition.energy_kcal is None:
        return None
    inputs = _calculation_inputs(composition)
    raw_energy = inputs.get("practical_energy")
    if inputs.get("practical_energy_used") is True and isinstance(raw_energy, dict):
        confidence = raw_energy.get("confidence")
        return confidence if isinstance(confidence, str) else "low"
    if int(inputs.get("estimated_portion_conversion_count") or 0) > 0:
        return "low"
    if inputs.get("serving_count_estimated") is True:
        return "medium"
    if int(inputs.get("qualitative_ingredient_count") or 0) > 0:
        return "medium"
    return "high"


def _serving_divisor(
    recipe: Recipe,
    composition: RecipeCompositionSnapshot,
) -> Decimal | None:
    if recipe.serving_count is not None:
        return recipe.serving_count
    if composition.reference_unit == "serving" and composition.reference_quantity > 0:
        return composition.reference_quantity
    return None


def _composition_read(
    recipe: Recipe,
    composition: RecipeCompositionSnapshot | None,
) -> RecipeCompositionRead | None:
    if composition is None:
        return None
    inputs = _calculation_inputs(composition)
    serving_divisor = _serving_divisor(recipe, composition)
    energy_per_serving = (
        composition.energy_kcal / serving_divisor
        if composition.energy_kcal is not None and serving_divisor is not None
        else None
    )
    return RecipeCompositionRead(
        id=composition.id,
        reference_quantity=composition.reference_quantity,
        reference_unit=composition.reference_unit,
        energy_kcal=composition.energy_kcal,
        energy_per_serving_kcal=energy_per_serving,
        energy_confidence=_energy_confidence(composition),
        serving_count_estimated=inputs.get("serving_count_estimated") is True,
        composition_version=composition.composition_version,
        calculation_version=composition.calculation_version,
        evidence=_composition_evidence(composition),
        practical_profile=_practical_profile_payload(composition),
        computed_at=composition.computed_at,
        nutrients=[
            RecipeNutrientRead(
                key=nutrient.nutrient_key,
                total_value=nutrient.value,
                unit=nutrient.unit,
                per_serving_value=(
                    nutrient.value / serving_divisor
                    if serving_divisor is not None
                    else None
                ),
            )
            for nutrient in composition.nutrients
        ],
    )


def _ingredient_read(ingredient: RecipeIngredient) -> RecipeIngredientRead:
    food_composition = (
        ingredient.food_item.compositions[-1]
        if ingredient.food_item.compositions
        else None
    )
    return RecipeIngredientRead(
        id=ingredient.id,
        food_item_id=ingredient.food_item_id,
        food_item_name=ingredient.food_item.name,
        quantity=ingredient.quantity,
        unit=ingredient.unit,
        preparation=ingredient.preparation,
        notes=ingredient.notes,
        sort_order=ingredient.sort_order,
        has_nutrition=food_composition is not None,
        has_energy=(
            food_composition is not None and food_composition.energy_kcal is not None
        ),
    )


def _recipe_read(recipe: Recipe) -> RecipeRead:
    composition = _latest_composition(recipe)
    is_shared = recipe.family_id is None
    return RecipeRead(
        id=recipe.id,
        family_id=recipe.family_id,
        scope="shared" if is_shared else "family",
        editable=not is_shared,
        recipe_key=recipe.recipe_key,
        name=recipe.name,
        description=recipe.description,
        suitable_meal_types=list(
            recipe.suitable_meal_types or recipe_default_meal_types(recipe.source)
        ),
        yield_quantity=recipe.yield_quantity,
        yield_unit=recipe.yield_unit,
        serving_count=recipe.serving_count,
        source=recipe.source,
        is_active=recipe.is_active,
        ingredients=[_ingredient_read(ingredient) for ingredient in recipe.ingredients],
        latest_composition=_composition_read(recipe, composition),
        nutrition_issues=_composition_issues(composition),
        created_at=recipe.created_at,
        updated_at=recipe.updated_at,
    )


def _ingredient_model(
    db: Session,
    family_id: uuid.UUID,
    ingredient_id: uuid.UUID,
) -> FoodItem:
    item = db.scalar(
        select(FoodItem)
        .options(
            selectinload(FoodItem.compositions).selectinload(
                FoodCompositionSnapshot.nutrients
            )
        )
        .where(
            FoodItem.id == ingredient_id,
            FoodItem.food_kind == "ingredient",
            FoodItem.is_active.is_(True),
            or_(FoodItem.family_id == family_id, FoodItem.family_id.is_(None)),
        )
    )
    if item is None:
        raise RecipeIngredientError(f"Ingredient {ingredient_id} is not available to this Family.")
    return item


def _build_ingredients(
    db: Session,
    family_id: uuid.UUID,
    values: list[RecipeIngredientWrite],
) -> list[RecipeIngredient]:
    return [
        RecipeIngredient(
            food_item=_ingredient_model(db, family_id, value.food_item_id),
            quantity=value.quantity,
            unit=value.unit.lower(),
            preparation=_optional_text(value.preparation),
            notes=_optional_text(value.notes),
            sort_order=index,
        )
        for index, value in enumerate(values)
    ]


def _validate_yield_shape(quantity: Decimal | None, unit: str | None) -> None:
    if (quantity is None) != (unit is None):
        raise RecipeCatalogueError("yield_quantity and yield_unit must be provided together.")


def list_family_recipes(
    db: Session,
    family_id: uuid.UUID,
    *,
    query: str | None = None,
    include_inactive: bool = False,
) -> list[RecipeRead]:
    if include_inactive:
        visibility = or_(
            Recipe.family_id == family_id,
            and_(Recipe.family_id.is_(None), Recipe.is_active.is_(True)),
        )
    else:
        visibility = and_(
            or_(Recipe.family_id == family_id, Recipe.family_id.is_(None)),
            Recipe.is_active.is_(True),
        )
    statement = (
        select(Recipe)
        .options(*_recipe_options())
        .where(visibility)
        .order_by(Recipe.name, Recipe.id)
    )
    if query and query.strip():
        statement = statement.where(Recipe.name.ilike(f"%{query.strip()}%"))
    return [_recipe_read(recipe) for recipe in db.scalars(statement).all()]


def get_family_recipe(
    db: Session,
    family_id: uuid.UUID,
    recipe_id: uuid.UUID,
) -> RecipeRead | None:
    recipe = db.scalar(
        select(Recipe)
        .options(*_recipe_options())
        .where(
            Recipe.id == recipe_id,
            or_(
                Recipe.family_id == family_id,
                and_(Recipe.family_id.is_(None), Recipe.is_active.is_(True)),
            ),
        )
    )
    return None if recipe is None else _recipe_read(recipe)


def get_family_recipe_model(
    db: Session,
    family_id: uuid.UUID,
    recipe_id: uuid.UUID,
) -> Recipe:
    recipe = db.scalar(
        select(Recipe)
        .options(*_recipe_options())
        .where(Recipe.id == recipe_id, Recipe.family_id == family_id)
    )
    if recipe is None:
        raise RecipeNotFoundError("Recipe not found or is a read-only shared Recipe")
    return recipe


def get_family_visible_recipe_model(
    db: Session,
    family_id: uuid.UUID,
    recipe_id: uuid.UUID,
) -> Recipe:
    """Return a Recipe the Family may consume, including active shared Recipes."""
    recipe = db.scalar(
        select(Recipe)
        .options(*_recipe_options())
        .where(
            Recipe.id == recipe_id,
            or_(
                Recipe.family_id == family_id,
                and_(Recipe.family_id.is_(None), Recipe.is_active.is_(True)),
            ),
        )
    )
    if recipe is None:
        raise RecipeNotFoundError("Recipe not found for this Family")
    return recipe


def create_family_recipe(db: Session, family: Family, data: RecipeCreate) -> RecipeRead:
    recipe = Recipe(
        family=family,
        recipe_key=f"family:{family.id}:recipe:{uuid.uuid4()}",
        name=data.name,
        description=_optional_text(data.description),
        suitable_meal_types=list(data.suitable_meal_types),
        yield_quantity=data.yield_quantity,
        yield_unit=data.yield_unit.lower() if data.yield_unit else None,
        serving_count=data.serving_count,
        source="user",
        source_reference="nutriflow-family-recipe-editor",
        is_active=True,
    )
    db.add(recipe)
    recipe.ingredients.extend(_build_ingredients(db, family.id, data.ingredients))
    db.flush()
    build_recipe_composition(recipe)
    db.commit()
    return _recipe_read(recipe)


def update_family_recipe(
    db: Session,
    family_id: uuid.UUID,
    recipe_id: uuid.UUID,
    data: RecipeUpdate,
) -> RecipeRead:
    recipe = get_family_recipe_model(db, family_id, recipe_id)
    fields = data.model_fields_set

    next_yield_quantity = (
        data.yield_quantity if "yield_quantity" in fields else recipe.yield_quantity
    )
    next_yield_unit = data.yield_unit if "yield_unit" in fields else recipe.yield_unit
    _validate_yield_shape(next_yield_quantity, next_yield_unit)

    if "name" in fields and data.name is not None:
        recipe.name = data.name
    if "description" in fields:
        recipe.description = _optional_text(data.description)
    if "suitable_meal_types" in fields and data.suitable_meal_types is not None:
        recipe.suitable_meal_types = list(data.suitable_meal_types)
    if "yield_quantity" in fields:
        recipe.yield_quantity = data.yield_quantity
    if "yield_unit" in fields:
        recipe.yield_unit = data.yield_unit.lower() if data.yield_unit else None
    if "serving_count" in fields:
        recipe.serving_count = data.serving_count
    if "is_active" in fields and data.is_active is not None:
        recipe.is_active = data.is_active
    if "ingredients" in fields and data.ingredients is not None:
        recipe.ingredients[:] = _build_ingredients(db, family_id, data.ingredients)

    nutrition_changed = bool(
        fields.intersection(
            {"name", "yield_quantity", "yield_unit", "serving_count", "ingredients"}
        )
    )
    if nutrition_changed:
        db.flush()
        build_recipe_composition(recipe)

    db.commit()
    return _recipe_read(recipe)


def deactivate_family_recipe(
    db: Session,
    family_id: uuid.UUID,
    recipe_id: uuid.UUID,
) -> None:
    recipe = get_family_recipe_model(db, family_id, recipe_id)
    recipe.is_active = False
    db.commit()
