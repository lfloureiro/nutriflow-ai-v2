import uuid
from datetime import UTC, datetime

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.family import Family
from app.models.food_catalog import (
    FoodCompositionSnapshot,
    FoodItem,
    FoodNutrientComponent,
    Recipe,
    RecipeIngredient,
)
from app.schemas.ingredient_catalogue import (
    IngredientCompositionRead,
    IngredientCompositionWrite,
    IngredientCreate,
    IngredientNutrientRead,
    IngredientRead,
    IngredientUpdate,
)
from app.services.recipe_nutrition import build_recipe_composition


class IngredientCatalogueError(ValueError):
    pass


class IngredientNotFoundError(IngredientCatalogueError):
    pass


def _optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _latest_composition(item: FoodItem) -> FoodCompositionSnapshot | None:
    if not item.compositions:
        return None
    return item.compositions[-1]


def _composition_read(
    composition: FoodCompositionSnapshot | None,
) -> IngredientCompositionRead | None:
    if composition is None:
        return None
    return IngredientCompositionRead(
        id=composition.id,
        reference_quantity=composition.reference_quantity,
        reference_unit=composition.reference_unit,
        energy_kcal=composition.energy_kcal,
        data_version=composition.data_version,
        source=composition.source,
        source_reference=composition.source_reference,
        effective_at=composition.effective_at,
        notes=composition.notes,
        nutrients=[
            IngredientNutrientRead(
                key=nutrient.nutrient_key,
                value=nutrient.value,
                unit=nutrient.unit,
            )
            for nutrient in sorted(
                composition.nutrients,
                key=lambda nutrient: nutrient.nutrient_key,
            )
        ],
    )


def _ingredient_read(
    item: FoodItem,
    family_id: uuid.UUID,
    *,
    recipe_usage_count: int = 0,
) -> IngredientRead:
    return IngredientRead(
        id=item.id,
        family_id=item.family_id,
        scope="shared" if item.family_id is None else "family",
        editable=item.family_id == family_id,
        catalog_key=item.catalog_key,
        name=item.name,
        brand=item.brand,
        description=item.description,
        source=item.source,
        is_active=item.is_active,
        recipe_usage_count=recipe_usage_count,
        latest_composition=_composition_read(_latest_composition(item)),
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _visible_recipe_usage_counts(
    db: Session,
    family_id: uuid.UUID,
    ingredient_ids: list[uuid.UUID],
) -> dict[uuid.UUID, int]:
    if not ingredient_ids:
        return {}
    rows = db.execute(
        select(
            RecipeIngredient.food_item_id,
            func.count(func.distinct(Recipe.id)),
        )
        .join(Recipe, Recipe.id == RecipeIngredient.recipe_id)
        .where(
            RecipeIngredient.food_item_id.in_(ingredient_ids),
            Recipe.is_active.is_(True),
            or_(Recipe.family_id == family_id, Recipe.family_id.is_(None)),
        )
        .group_by(RecipeIngredient.food_item_id)
    ).all()
    return {ingredient_id: int(count) for ingredient_id, count in rows}


def _visible_recipe_usage_count(
    db: Session,
    family_id: uuid.UUID,
    ingredient_id: uuid.UUID,
) -> int:
    return _visible_recipe_usage_counts(db, family_id, [ingredient_id]).get(ingredient_id, 0)


def _append_composition(
    item: FoodItem,
    data: IngredientCompositionWrite,
) -> FoodCompositionSnapshot:
    composition = FoodCompositionSnapshot(
        reference_quantity=data.reference_quantity,
        reference_unit=data.reference_unit.lower(),
        energy_kcal=data.energy_kcal,
        data_version=f"manual-{uuid.uuid4()}",
        source="user",
        source_reference="nutriflow-family-editor",
        effective_at=datetime.now(UTC),
        notes=_optional_text(data.notes),
    )
    composition.nutrients.extend(
        FoodNutrientComponent(
            nutrient_key=nutrient.key.lower(),
            value=nutrient.value,
            unit=nutrient.unit.lower(),
        )
        for nutrient in data.nutrients
    )
    item.compositions.append(composition)
    return composition


def _recalculate_recipes_using_ingredient(
    db: Session,
    family_id: uuid.UUID,
    ingredient_id: uuid.UUID,
) -> None:
    recipes = db.scalars(
        select(Recipe)
        .join(RecipeIngredient)
        .options(
            selectinload(Recipe.ingredients)
            .selectinload(RecipeIngredient.food_item)
            .selectinload(FoodItem.compositions)
            .selectinload(FoodCompositionSnapshot.nutrients),
            selectinload(Recipe.compositions),
        )
        .where(
            Recipe.family_id == family_id,
            RecipeIngredient.food_item_id == ingredient_id,
        )
    ).unique()
    for recipe in recipes:
        build_recipe_composition(recipe)


def list_family_ingredients(
    db: Session,
    family_id: uuid.UUID,
    *,
    query: str | None = None,
    include_inactive: bool = False,
) -> list[IngredientRead]:
    statement = (
        select(FoodItem)
        .options(
            selectinload(FoodItem.compositions).selectinload(
                FoodCompositionSnapshot.nutrients
            )
        )
        .where(
            or_(FoodItem.family_id == family_id, FoodItem.family_id.is_(None)),
            FoodItem.food_kind == "ingredient",
        )
        .order_by(FoodItem.name, FoodItem.id)
    )
    if not include_inactive:
        statement = statement.where(FoodItem.is_active.is_(True))
    if query and query.strip():
        pattern = f"%{query.strip()}%"
        statement = statement.where(
            or_(
                FoodItem.name.ilike(pattern),
                FoodItem.brand.ilike(pattern),
            )
        )
    items = list(db.scalars(statement).all())
    usage = _visible_recipe_usage_counts(db, family_id, [item.id for item in items])
    return [
        _ingredient_read(item, family_id, recipe_usage_count=usage.get(item.id, 0))
        for item in items
    ]


def get_family_ingredient(
    db: Session,
    family_id: uuid.UUID,
    ingredient_id: uuid.UUID,
) -> IngredientRead | None:
    item = db.scalar(
        select(FoodItem)
        .options(
            selectinload(FoodItem.compositions).selectinload(
                FoodCompositionSnapshot.nutrients
            )
        )
        .where(
            FoodItem.id == ingredient_id,
            or_(FoodItem.family_id == family_id, FoodItem.family_id.is_(None)),
            FoodItem.food_kind == "ingredient",
        )
    )
    if item is None:
        return None
    return _ingredient_read(
        item,
        family_id,
        recipe_usage_count=_visible_recipe_usage_count(db, family_id, item.id),
    )


def _get_family_ingredient_model(
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
            FoodItem.family_id == family_id,
            FoodItem.food_kind == "ingredient",
        )
    )
    if item is None:
        raise IngredientNotFoundError("Ingredient not found")
    return item


def create_family_ingredient(
    db: Session,
    family: Family,
    data: IngredientCreate,
) -> IngredientRead:
    item = FoodItem(
        family=family,
        catalog_key=f"family:{family.id}:ingredient:{uuid.uuid4()}",
        name=data.name,
        food_kind="ingredient",
        brand=_optional_text(data.brand),
        description=_optional_text(data.description),
        source="user",
        source_reference="nutriflow-family-editor",
        is_active=True,
    )
    db.add(item)
    if data.composition is not None:
        _append_composition(item, data.composition)
    db.commit()
    return _ingredient_read(item, family.id, recipe_usage_count=0)


def update_family_ingredient(
    db: Session,
    family_id: uuid.UUID,
    ingredient_id: uuid.UUID,
    data: IngredientUpdate,
) -> IngredientRead:
    item = _get_family_ingredient_model(db, family_id, ingredient_id)
    fields = data.model_fields_set
    if "name" in fields and data.name is not None:
        item.name = data.name
    if "brand" in fields:
        item.brand = _optional_text(data.brand)
    if "description" in fields:
        item.description = _optional_text(data.description)
    if "is_active" in fields and data.is_active is not None:
        item.is_active = data.is_active
    if "composition" in fields and data.composition is not None:
        _append_composition(item, data.composition)
        db.flush()
        _recalculate_recipes_using_ingredient(db, family_id, item.id)
    db.commit()
    return _ingredient_read(
        item,
        family_id,
        recipe_usage_count=_visible_recipe_usage_count(db, family_id, item.id),
    )


def deactivate_family_ingredient(
    db: Session,
    family_id: uuid.UUID,
    ingredient_id: uuid.UUID,
) -> None:
    item = _get_family_ingredient_model(db, family_id, ingredient_id)
    item.is_active = False
    db.commit()
