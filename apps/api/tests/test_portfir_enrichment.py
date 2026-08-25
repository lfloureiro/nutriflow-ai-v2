from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.food_catalog import FoodItem, Recipe, RecipeIngredient
from app.services.portfir import PortfirFoodNutrition, PortfirNutrient
from app.services.portfir_enrichment import auto_enrich_shared_ingredients_from_portfir

NOW = datetime(2026, 8, 25, 10, 0, tzinfo=UTC)


def _food(
    code: str,
    name: str,
    energy: str,
    *,
    reference_unit: str = "g",
) -> PortfirFoodNutrition:
    return PortfirFoodNutrition(
        code=code,
        name=name,
        energy_kcal=Decimal(energy),
        nutrients=(
            PortfirNutrient(key="protein", value=Decimal("1.2"), unit="g"),
        ),
        reference_unit=reference_unit,
    )


def test_auto_portfir_enrichment_applies_unique_high_confidence_match(
    db_session: Session,
) -> None:
    onion = FoodItem(
        catalog_key="legacy-v1:ingredient:onion",
        name="Cebola picada congelada",
        food_kind="ingredient",
        source="legacy-v1",
    )
    recipe = Recipe(
        recipe_key="legacy-v1:recipe:onion",
        name="Cebola teste",
        serving_count=Decimal(1),
        source="legacy-v1",
    )
    recipe.ingredients.append(
        RecipeIngredient(
            food_item=onion,
            quantity=Decimal(100),
            unit="g",
            sort_order=0,
        )
    )
    db_session.add(recipe)
    db_session.flush()

    result = auto_enrich_shared_ingredients_from_portfir(
        db_session,
        foods=(
            _food("101", "Cebola, crua", "29"),
            _food("102", "Cebolinho, cru", "30"),
        ),
        apply=True,
    )
    db_session.flush()

    item = next(entry for entry in result if entry.catalog_key == onion.catalog_key)
    assert item.status == "applied"
    assert item.matched_code == "101"
    assert item.confidence == Decimal("0.990")
    assert item.composition_created is True
    assert item.recalculated_recipe_count == 1
    assert onion.compositions[-1].source == "portfir"
    assert onion.compositions[-1].energy_kcal == Decimal("29.0000")
    assert recipe.compositions[-1].energy_kcal == Decimal("29.0000")


def test_portfir_volume_reference_recalculates_recipe_without_density_guess(
    db_session: Session,
) -> None:
    wine = FoodItem(
        catalog_key="legacy-v1:ingredient:white-wine",
        name="Vinho branco",
        food_kind="ingredient",
        source="legacy-v1",
    )
    recipe = Recipe(
        recipe_key="legacy-v1:recipe:wine",
        name="Receita com vinho",
        serving_count=Decimal(1),
        source="legacy-v1",
    )
    recipe.ingredients.append(
        RecipeIngredient(
            food_item=wine,
            quantity=Decimal(150),
            unit="ml",
            sort_order=0,
        )
    )
    db_session.add(recipe)
    db_session.flush()

    result = auto_enrich_shared_ingredients_from_portfir(
        db_session,
        foods=(_food("301", "Vinho branco", "72", reference_unit="ml"),),
        apply=True,
    )
    db_session.flush()

    item = next(entry for entry in result if entry.catalog_key == wine.catalog_key)
    assert item.status == "applied"
    assert wine.compositions[-1].reference_unit == "ml"
    assert recipe.compositions[-1].energy_kcal == Decimal("108.0000")


def test_auto_portfir_enrichment_leaves_ambiguous_match_for_review(
    db_session: Session,
) -> None:
    olive_oil = FoodItem(
        catalog_key="legacy-v1:ingredient:oil",
        name="Azeite",
        food_kind="ingredient",
        source="legacy-v1",
    )
    db_session.add(olive_oil)
    db_session.flush()

    result = auto_enrich_shared_ingredients_from_portfir(
        db_session,
        foods=(
            _food("201", "Azeite", "899"),
            _food("202", "Azeite", "900"),
        ),
        apply=True,
    )

    item = next(entry for entry in result if entry.catalog_key == olive_oil.catalog_key)
    assert item.status == "review"
    assert item.composition_created is False
    assert olive_oil.compositions == []