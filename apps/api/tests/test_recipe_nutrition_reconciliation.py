from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.food_catalog import (
    FoodCompositionSnapshot,
    FoodItem,
    Recipe,
    RecipeCompositionSnapshot,
    RecipeIngredient,
)
from app.services.recipe_nutrition_reconciliation import (
    reconcile_legacy_recipe_nutrition,
)

NOW = datetime(2026, 8, 25, 12, 0, tzinfo=UTC)


def _legacy_recipe(db_session: Session) -> tuple[Recipe, FoodItem]:
    ingredient = FoodItem(
        catalog_key="legacy-v1:ingredient:test",
        name="Ingrediente",
        food_kind="ingredient",
        source="legacy-v1",
    )
    ingredient.compositions.append(
        FoodCompositionSnapshot(
            reference_quantity=Decimal(100),
            reference_unit="g",
            energy_kcal=Decimal(250),
            data_version="test-v1",
            source="portfir",
            effective_at=NOW,
        )
    )
    recipe = Recipe(
        recipe_key="legacy-v1:recipe:test",
        name="Receita",
        source="legacy-v1",
    )
    recipe.ingredients.append(
        RecipeIngredient(
            food_item=ingredient,
            quantity=Decimal(200),
            unit="g",
            sort_order=0,
        )
    )
    db_session.add(recipe)
    db_session.flush()
    return recipe, ingredient


def test_reconciliation_builds_recipe_from_existing_ingredient_composition(
    db_session: Session,
) -> None:
    recipe, _ = _legacy_recipe(db_session)

    first = reconcile_legacy_recipe_nutrition(db_session)
    second = reconcile_legacy_recipe_nutrition(db_session)

    assert first.total_count == 1
    assert first.rebuilt_count == 1
    assert first.calculated_count == 1
    assert first.estimated_count == 0
    assert first.blocked_count == 0
    assert second.rebuilt_count == 0
    assert db_session.scalar(
        select(func.count()).select_from(RecipeCompositionSnapshot)
    ) == 1
    assert recipe.compositions[-1].energy_kcal == Decimal(500)


def test_reconciliation_rebuilds_when_ingredient_snapshot_changes(
    db_session: Session,
) -> None:
    recipe, ingredient = _legacy_recipe(db_session)
    reconcile_legacy_recipe_nutrition(db_session)

    ingredient.compositions.append(
        FoodCompositionSnapshot(
            reference_quantity=Decimal(100),
            reference_unit="g",
            energy_kcal=Decimal(300),
            data_version="test-v2",
            source="portfir",
            effective_at=NOW + timedelta(days=1),
        )
    )
    db_session.flush()

    result = reconcile_legacy_recipe_nutrition(db_session)

    assert result.rebuilt_count == 1
    assert result.calculated_count == 1
    assert db_session.scalar(
        select(func.count()).select_from(RecipeCompositionSnapshot)
    ) == 2
    assert recipe.compositions[-1].energy_kcal == Decimal(600)
