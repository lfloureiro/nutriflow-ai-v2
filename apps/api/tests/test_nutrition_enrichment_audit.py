import json
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.food_catalog import (
    FoodCompositionSnapshot,
    FoodItem,
    Recipe,
    RecipeIngredient,
)
from app.services.nutrition_enrichment_audit import (
    build_shared_ingredient_enrichment_audit,
)

NOW = datetime(2026, 8, 24, 12, 0, tzinfo=UTC)


def _ingredient(
    key: str,
    name: str,
    *,
    with_composition: bool = True,
    energy: Decimal | None = Decimal(100),
    notes: str | None = None,
) -> FoodItem:
    item = FoodItem(
        catalog_key=key,
        name=name,
        food_kind="ingredient",
        source="legacy-v1",
    )
    if with_composition:
        item.compositions.append(
            FoodCompositionSnapshot(
                reference_quantity=Decimal(100),
                reference_unit="g",
                energy_kcal=energy,
                data_version=f"test-{key}",
                source="test",
                effective_at=NOW,
                notes=notes,
            )
        )
    return item


def _use(
    db_session: Session,
    item: FoodItem,
    *,
    recipe_key: str,
    unit: str,
) -> None:
    recipe = Recipe(
        recipe_key=recipe_key,
        name=recipe_key,
        serving_count=Decimal(1),
        source="test",
    )
    recipe.ingredients.append(
        RecipeIngredient(
            food_item=item,
            quantity=Decimal(1),
            unit=unit,
            sort_order=0,
        )
    )
    db_session.add(recipe)


def test_enrichment_audit_distinguishes_nutrition_and_unit_blockers(
    db_session: Session,
) -> None:
    missing_composition = _ingredient(
        "shared:missing-composition",
        "Sem composição",
        with_composition=False,
    )
    missing_energy = _ingredient(
        "shared:missing-energy",
        "Sem energia",
        energy=None,
    )
    blocked_unit = _ingredient(
        "shared:blocked-unit",
        "Sem conversão",
        energy=Decimal(200),
    )
    ready_direct = _ingredient(
        "shared:ready-direct",
        "Pronto em gramas",
        energy=Decimal(100),
    )
    ready_portion = _ingredient(
        "shared:ready-portion",
        "Pronto por unidade",
        energy=Decimal(150),
        notes=json.dumps(
            {
                "portion_conversions": {
                    "un": {
                        "reference_unit": "g",
                        "quantity_in_reference_unit": "50",
                    }
                }
            }
        ),
    )

    _use(
        db_session,
        missing_composition,
        recipe_key="recipe:missing-composition",
        unit="g",
    )
    _use(
        db_session,
        missing_energy,
        recipe_key="recipe:missing-energy",
        unit="g",
    )
    _use(
        db_session,
        blocked_unit,
        recipe_key="recipe:blocked-unit",
        unit="un",
    )
    _use(
        db_session,
        ready_direct,
        recipe_key="recipe:ready-direct",
        unit="kg",
    )
    _use(
        db_session,
        ready_portion,
        recipe_key="recipe:ready-portion",
        unit="un",
    )
    db_session.flush()

    by_key = {
        item.catalog_key: item
        for item in build_shared_ingredient_enrichment_audit(db_session)
    }

    assert by_key["shared:missing-composition"].status == "missing_composition"
    assert by_key["shared:missing-energy"].status == "missing_energy"
    assert by_key["shared:blocked-unit"].status == "missing_unit_conversion"
    assert by_key["shared:blocked-unit"].blocking_units == ("un",)
    assert by_key["shared:ready-direct"].status == "ready"
    assert by_key["shared:ready-portion"].status == "ready"
    assert by_key["shared:ready-portion"].recipe_units == ("un",)
    assert by_key["shared:ready-portion"].recipe_usage_count == 1
