import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.food_catalog import (
    FoodCompositionSnapshot,
    FoodItem,
    FoodNutrientComponent,
    Recipe,
    RecipeIngredient,
)
from app.services.fooddata_central import FdcFoodNutrition, GENERIC_DATA_TYPES
from app.services.recipe_nutrition import build_recipe_composition


class SharedIngredientEnrichmentError(ValueError):
    pass


@dataclass(frozen=True)
class SharedIngredientEnrichmentResult:
    ingredient_id: uuid.UUID
    catalog_key: str
    composition_id: uuid.UUID
    data_version: str
    created: bool
    recalculated_recipe_ids: tuple[uuid.UUID, ...]


def _data_version(food: FdcFoodNutrition) -> str:
    publication = (food.publication_date or "unknown").replace("/", "-")
    return f"usda-fdc-{food.fdc_id}-{publication}"[:64]


def _shared_ingredient(
    db: Session,
    *,
    catalog_key: str,
) -> FoodItem:
    item = db.scalar(
        select(FoodItem)
        .options(
            selectinload(FoodItem.compositions).selectinload(
                FoodCompositionSnapshot.nutrients
            )
        )
        .where(
            FoodItem.catalog_key == catalog_key,
            FoodItem.family_id.is_(None),
            FoodItem.food_kind == "ingredient",
        )
    )
    if item is None:
        raise SharedIngredientEnrichmentError(
            f"Shared ingredient {catalog_key!r} was not found."
        )
    return item


def _recipes_using_ingredient(
    db: Session,
    ingredient_id: uuid.UUID,
) -> list[Recipe]:
    return list(
        db.scalars(
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
                RecipeIngredient.food_item_id == ingredient_id,
                Recipe.is_active.is_(True),
            )
        )
        .unique()
        .all()
    )


def apply_fdc_nutrition_to_shared_ingredient(
    db: Session,
    *,
    catalog_key: str,
    food: FdcFoodNutrition,
    effective_at: datetime | None = None,
) -> SharedIngredientEnrichmentResult:
    if food.data_type not in GENERIC_DATA_TYPES:
        raise SharedIngredientEnrichmentError(
            f"FoodData Central data type {food.data_type!r} is not approved for generic ingredients."
        )
    if food.energy_kcal is None:
        raise SharedIngredientEnrichmentError(
            "Approved FoodData Central match does not contain kcal energy."
        )

    item = _shared_ingredient(db, catalog_key=catalog_key)
    data_version = _data_version(food)
    existing = next(
        (
            composition
            for composition in item.compositions
            if composition.data_version == data_version
        ),
        None,
    )
    if existing is not None:
        return SharedIngredientEnrichmentResult(
            ingredient_id=item.id,
            catalog_key=item.catalog_key,
            composition_id=existing.id,
            data_version=data_version,
            created=False,
            recalculated_recipe_ids=(),
        )

    composition = FoodCompositionSnapshot(
        reference_quantity=100,
        reference_unit="g",
        energy_kcal=food.energy_kcal,
        data_version=data_version,
        source="usda-fdc",
        source_reference=food.source_reference,
        effective_at=effective_at or datetime.now(UTC),
        notes=json.dumps(
            {
                "fdc_id": food.fdc_id,
                "description": food.description,
                "data_type": food.data_type,
                "publication_date": food.publication_date,
                "reference_basis": "100 g edible portion",
                "curation": "explicitly-approved-match",
            },
            sort_keys=True,
        ),
    )
    composition.nutrients.extend(
        FoodNutrientComponent(
            nutrient_key=nutrient.key,
            value=nutrient.value,
            unit=nutrient.unit,
        )
        for nutrient in food.nutrients
    )
    item.compositions.append(composition)
    db.flush()

    recipes = _recipes_using_ingredient(db, item.id)
    for recipe in recipes:
        build_recipe_composition(recipe)
    db.flush()

    return SharedIngredientEnrichmentResult(
        ingredient_id=item.id,
        catalog_key=item.catalog_key,
        composition_id=composition.id,
        data_version=data_version,
        created=True,
        recalculated_recipe_ids=tuple(recipe.id for recipe in recipes),
    )
