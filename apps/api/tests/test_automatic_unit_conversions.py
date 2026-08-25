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
from app.services import automatic_unit_conversions
from app.services.fooddata_central import FdcFoodNutrition, FdcFoodPortion

NOW = datetime(2026, 8, 25, 12, 0, tzinfo=UTC)


def _olive_oil() -> FoodItem:
    item = FoodItem(
        catalog_key="legacy-v1:ingredient:olive-oil",
        name="Azeite",
        food_kind="ingredient",
        source="legacy-v1",
    )
    item.compositions.append(
        FoodCompositionSnapshot(
            reference_quantity=Decimal(100),
            reference_unit="g",
            energy_kcal=Decimal(899),
            data_version="portfir-7.1-2026-A1-g",
            source="portfir",
            source_reference="https://portfir.example/A1",
            effective_at=NOW,
        )
    )
    return item


def _usda_olive_oil() -> FdcFoodNutrition:
    return FdcFoodNutrition(
        fdc_id=748608,
        description="Oil, olive, salad or cooking",
        data_type="Foundation",
        publication_date="10/31/2024",
        energy_kcal=Decimal(884),
        nutrients=(),
        portions=(
            FdcFoodPortion(
                portion_id=1,
                amount=Decimal(1),
                gram_weight=Decimal(216),
                description="1 cup",
                measure_unit="cup",
                modifier=None,
            ),
        ),
    )


def test_auto_unit_conversion_keeps_portfir_nutrition_and_marks_estimate(
    db_session: Session,
    monkeypatch,
) -> None:
    oil = _olive_oil()
    recipe = Recipe(
        recipe_key="legacy-v1:recipe:oil-test",
        name="Receita com azeite",
        serving_count=Decimal(1),
        source="legacy-v1",
    )
    recipe.ingredients.append(
        RecipeIngredient(
            food_item=oil,
            quantity=Decimal(10),
            unit="ml",
            sort_order=0,
        )
    )
    db_session.add(recipe)
    db_session.flush()

    monkeypatch.setattr(
        automatic_unit_conversions,
        "_matching_food",
        lambda _spec: _usda_olive_oil(),
    )

    result = automatic_unit_conversions.auto_enrich_shared_unit_conversions(db_session)
    db_session.flush()

    assert len(result) == 1
    assert result[0].created is True
    assert result[0].recipe_unit == "ml"

    composition = oil.compositions[-1]
    assert composition.source == "portfir"
    assert composition.energy_kcal == Decimal("899.0000")
    assert composition.notes is not None
    notes = json.loads(composition.notes)
    conversion = notes["portion_conversions"]["ml"]
    assert conversion["source"] == "usda-fdc"
    assert conversion["estimated"] is True
    assert Decimal(conversion["quantity_in_reference_unit"]) == Decimal("0.9")

    recipe_composition = recipe.compositions[-1]
    assert recipe_composition.energy_kcal == Decimal("80.9100")
    assert recipe_composition.calculation_inputs["energy_estimated"] is True
    assert recipe_composition.calculation_inputs["estimated_portion_conversion_count"] == 1


def test_auto_unit_conversion_skips_usda_when_reference_unit_is_compatible(
    db_session: Session,
    monkeypatch,
) -> None:
    oil = _olive_oil()
    oil.compositions[-1].reference_unit = "ml"
    recipe = Recipe(
        recipe_key="legacy-v1:recipe:oil-direct",
        name="Receita com azeite direto",
        serving_count=Decimal(1),
        source="legacy-v1",
    )
    recipe.ingredients.append(
        RecipeIngredient(
            food_item=oil,
            quantity=Decimal(10),
            unit="ml",
            sort_order=0,
        )
    )
    db_session.add(recipe)
    db_session.flush()

    def fail_matching(_spec):
        raise AssertionError("USDA must not be queried for compatible units")

    monkeypatch.setattr(automatic_unit_conversions, "_matching_food", fail_matching)

    result = automatic_unit_conversions.auto_enrich_shared_unit_conversions(db_session)

    assert result == ()
