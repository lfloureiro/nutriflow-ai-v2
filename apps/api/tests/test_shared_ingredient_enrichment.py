from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.food_catalog import (
    FoodCompositionSnapshot,
    FoodItem,
    Recipe,
    RecipeCompositionSnapshot,
    RecipeIngredient,
)
from app.services.fooddata_central import FdcFoodNutrition, FdcNutrient
from app.services.shared_ingredient_enrichment import (
    SharedIngredientEnrichmentError,
    apply_fdc_nutrition_to_shared_ingredient,
)

NOW = datetime(2026, 8, 24, 12, 0, tzinfo=UTC)


def _nutrition(*, data_type: str = "Foundation") -> FdcFoodNutrition:
    return FdcFoodNutrition(
        fdc_id=123,
        description="Garlic, raw",
        data_type=data_type,
        publication_date="4/1/2026",
        energy_kcal=Decimal(149),
        nutrients=(
            FdcNutrient(key="protein", value=Decimal("6.36"), unit="g"),
            FdcNutrient(key="carbohydrate", value=Decimal("33.06"), unit="g"),
        ),
    )


def _shared_recipe(db_session: Session) -> tuple[FoodItem, Recipe]:
    ingredient = FoodItem(
        catalog_key="legacy-v1:ingredient:garlic",
        name="Alho",
        food_kind="ingredient",
        source="legacy-v1",
    )
    recipe = Recipe(
        recipe_key="legacy-v1:recipe:garlic-test",
        name="Receita de alho",
        serving_count=Decimal(1),
        source="legacy-v1",
    )
    recipe.ingredients.append(
        RecipeIngredient(
            food_item=ingredient,
            quantity=Decimal(100),
            unit="g",
            sort_order=0,
        )
    )
    db_session.add(recipe)
    db_session.flush()
    return ingredient, recipe


def test_fdc_enrichment_versions_shared_ingredient_and_recalculates_recipe(
    db_session: Session,
) -> None:
    ingredient, recipe = _shared_recipe(db_session)

    result = apply_fdc_nutrition_to_shared_ingredient(
        db_session,
        catalog_key=ingredient.catalog_key,
        food=_nutrition(),
        effective_at=NOW,
    )
    db_session.flush()

    assert result.created
    assert result.ingredient_id == ingredient.id
    assert result.recalculated_recipe_ids == (recipe.id,)
    assert db_session.scalar(select(func.count()).select_from(FoodCompositionSnapshot)) == 1
    assert db_session.scalar(select(func.count()).select_from(RecipeCompositionSnapshot)) == 1

    composition = ingredient.compositions[-1]
    assert composition.reference_quantity == Decimal("100.0000")
    assert composition.reference_unit == "g"
    assert composition.energy_kcal == Decimal("149.0000")
    assert composition.source == "usda-fdc"
    assert composition.source_reference is not None
    assert "food-details/123/nutrients" in composition.source_reference

    recipe_composition = recipe.compositions[-1]
    assert recipe_composition.energy_kcal == Decimal("149.0000")
    assert recipe_composition.calculation_version == "recipe-nutrition-v1"


def test_fdc_enrichment_is_idempotent_for_same_source_version(
    db_session: Session,
) -> None:
    ingredient, recipe = _shared_recipe(db_session)
    first = apply_fdc_nutrition_to_shared_ingredient(
        db_session,
        catalog_key=ingredient.catalog_key,
        food=_nutrition(),
        effective_at=NOW,
    )
    db_session.flush()
    second = apply_fdc_nutrition_to_shared_ingredient(
        db_session,
        catalog_key=ingredient.catalog_key,
        food=_nutrition(),
        effective_at=NOW,
    )
    db_session.flush()

    assert first.composition_id == second.composition_id
    assert not second.created
    assert second.recalculated_recipe_ids == ()
    assert db_session.scalar(select(func.count()).select_from(FoodCompositionSnapshot)) == 1
    assert db_session.scalar(select(func.count()).select_from(RecipeCompositionSnapshot)) == 1
    assert recipe.compositions[-1].energy_kcal == Decimal("149.0000")


def test_fdc_enrichment_rejects_non_generic_data_type(db_session: Session) -> None:
    ingredient, _ = _shared_recipe(db_session)

    with pytest.raises(SharedIngredientEnrichmentError, match="not approved"):
        apply_fdc_nutrition_to_shared_ingredient(
            db_session,
            catalog_key=ingredient.catalog_key,
            food=_nutrition(data_type="Branded"),
            effective_at=NOW,
        )
