from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.food_catalog import FoodItem, Recipe, RecipeIngredient
from app.services.legacy_v1_unit_corrections import (
    apply_verified_legacy_v1_unit_corrections,
)


def _row(
    db_session: Session,
    *,
    recipe_key: str,
    ingredient_key: str,
    quantity: Decimal,
    unit: str,
) -> RecipeIngredient:
    ingredient = FoodItem(
        catalog_key=ingredient_key,
        name="Ingrediente",
        food_kind="ingredient",
        source="legacy-v1",
    )
    recipe = Recipe(
        recipe_key=recipe_key,
        name="Receita",
        source="legacy-v1",
    )
    row = RecipeIngredient(
        food_item=ingredient,
        quantity=quantity,
        unit=unit,
        sort_order=0,
        notes="Importado do snapshot real NutriFlow v1.",
    )
    recipe.ingredients.append(row)
    db_session.add(recipe)
    db_session.flush()
    return row


def test_verified_v1_unit_anomaly_is_corrected_idempotently(
    db_session: Session,
) -> None:
    row = _row(
        db_session,
        recipe_key="legacy-v1:recipe:15",
        ingredient_key="legacy-v1:ingredient:148",
        quantity=Decimal(100),
        unit="un",
    )

    first = apply_verified_legacy_v1_unit_corrections(db_session)
    second = apply_verified_legacy_v1_unit_corrections(db_session)

    assert first.corrected_count == 1
    assert second.corrected_count == 0
    assert row.unit == "ml"
    assert row.notes is not None
    assert "anomalia verificada" in row.notes


def test_unlisted_legacy_row_is_not_changed(db_session: Session) -> None:
    row = _row(
        db_session,
        recipe_key="legacy-v1:recipe:99",
        ingredient_key="legacy-v1:ingredient:148",
        quantity=Decimal(1),
        unit="un",
    )

    result = apply_verified_legacy_v1_unit_corrections(db_session)

    assert result.corrected_count == 0
    assert row.unit == "un"
