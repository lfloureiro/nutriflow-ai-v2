from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.models.family import Family
from app.models.food_catalog import (
    FoodCompositionSnapshot,
    FoodItem,
    Recipe,
    RecipeCompositionSnapshot,
    RecipeIngredient,
)
from app.models.pantry_stock import PantryStockLot
from app.services.meal_recommendation import build_food_candidate, build_recipe_candidate
from app.services.pantry_planning import (
    PantryPlanningError,
    PantryUnitConversionError,
    assess_food_pantry_stock,
    build_pantry_stock_practical_profiles,
    evaluate_recipe_pantry_sufficiency,
)

AS_OF = datetime(2026, 8, 22, 12, 0, tzinfo=UTC)


def _persist_family(db_session: Session, name: str = "Pantry Family") -> Family:
    family = Family(name=name, timezone="Europe/Lisbon")
    db_session.add(family)
    db_session.flush()
    return family


def _persist_food(
    db_session: Session,
    family: Family,
    *,
    key: str,
    name: str,
) -> FoodItem:
    food_item = FoodItem(
        family=family,
        catalog_key=key,
        name=name,
        food_kind="ingredient",
        source="test",
    )
    db_session.add(food_item)
    db_session.flush()
    return food_item


def _add_stock(
    db_session: Session,
    family: Family,
    food_item: FoodItem,
    *,
    stock_key: str,
    quantity: str,
    unit: str,
    expires_at: datetime | None = None,
    is_available: bool = True,
) -> PantryStockLot:
    if family.id is None or food_item.id is None:
        raise AssertionError("Pantry fixtures must be persisted.")
    lot = PantryStockLot(
        family_id=family.id,
        food_item_id=food_item.id,
        stock_key=stock_key,
        quantity_available=Decimal(quantity),
        unit=unit,
        expires_at=expires_at,
        is_available=is_available,
        source="test",
        observed_at=AS_OF - timedelta(hours=1),
    )
    db_session.add(lot)
    db_session.flush()
    return lot


def _persist_recipe(
    db_session: Session,
    family: Family,
    *,
    key: str,
    ingredients: list[tuple[FoodItem, str, str]],
    yield_quantity: str = "400.0000",
    yield_unit: str = "g",
) -> Recipe:
    recipe = Recipe(
        family=family,
        recipe_key=key,
        name="Pantry recipe",
        yield_quantity=Decimal(yield_quantity),
        yield_unit=yield_unit,
        source="test",
    )
    recipe.ingredients = [
        RecipeIngredient(
            food_item=food_item,
            quantity=Decimal(quantity),
            unit=unit,
            sort_order=index,
        )
        for index, (food_item, quantity, unit) in enumerate(ingredients)
    ]
    db_session.add(recipe)
    db_session.flush()
    return recipe


def test_food_stock_aggregates_safe_units_and_ignores_expired_lots(
    db_session: Session,
) -> None:
    family = _persist_family(db_session)
    flour = _persist_food(db_session, family, key="food:flour", name="Flour")
    _add_stock(
        db_session,
        family,
        flour,
        stock_key="flour-500g",
        quantity="500.0000",
        unit="g",
        expires_at=AS_OF + timedelta(days=10),
    )
    _add_stock(
        db_session,
        family,
        flour,
        stock_key="flour-half-kg",
        quantity="0.5000",
        unit="kg",
        expires_at=AS_OF + timedelta(days=20),
    )
    _add_stock(
        db_session,
        family,
        flour,
        stock_key="flour-expired",
        quantity="100.0000",
        unit="g",
        expires_at=AS_OF - timedelta(seconds=1),
    )

    if family.id is None:
        raise AssertionError("Family must be persisted.")
    assessment = assess_food_pantry_stock(
        db_session,
        family_id=family.id,
        food_item=flour,
        required_quantity=Decimal("900.0000"),
        required_unit="g",
        as_of=AS_OF,
    )

    assert assessment.available_quantity == Decimal("1000.0000")
    assert assessment.missing_quantity == Decimal("0.0000")
    assert assessment.is_sufficient is True
    assert len(assessment.stock_lot_ids) == 2


def test_recipe_shortage_generates_exact_shopping_requirement(db_session: Session) -> None:
    family = _persist_family(db_session, "Shopping Family")
    pasta = _persist_food(db_session, family, key="food:pasta-dry", name="Pasta")
    sauce = _persist_food(db_session, family, key="food:sauce", name="Sauce")
    recipe = _persist_recipe(
        db_session,
        family,
        key="recipe:pasta",
        ingredients=[
            (pasta, "300.0000", "g"),
            (sauce, "150.0000", "g"),
        ],
    )
    _add_stock(
        db_session,
        family,
        pasta,
        stock_key="pasta-stock",
        quantity="100.0000",
        unit="g",
    )
    _add_stock(
        db_session,
        family,
        sauce,
        stock_key="sauce-stock",
        quantity="200.0000",
        unit="g",
    )

    if family.id is None:
        raise AssertionError("Family must be persisted.")
    result = evaluate_recipe_pantry_sufficiency(
        db_session,
        family_id=family.id,
        recipe=recipe,
        as_of=AS_OF,
    )

    assert result.is_sufficient is False
    assert len(result.shopping_requirements) == 1
    requirement = result.shopping_requirements[0]
    assert requirement.catalog_key == "food:pasta-dry"
    assert requirement.quantity == Decimal("200.0000")
    assert requirement.unit == "g"


def test_duplicate_recipe_ingredients_are_aggregated_before_stock_comparison(
    db_session: Session,
) -> None:
    family = _persist_family(db_session, "Duplicate Ingredient Family")
    flour = _persist_food(db_session, family, key="food:duplicate-flour", name="Flour")
    recipe = _persist_recipe(
        db_session,
        family,
        key="recipe:bread",
        ingredients=[
            (flour, "100.0000", "g"),
            (flour, "0.1000", "kg"),
        ],
    )
    _add_stock(
        db_session,
        family,
        flour,
        stock_key="bread-flour-stock",
        quantity="350.0000",
        unit="g",
    )

    if family.id is None:
        raise AssertionError("Family must be persisted.")
    result = evaluate_recipe_pantry_sufficiency(
        db_session,
        family_id=family.id,
        recipe=recipe,
        as_of=AS_OF,
        batch_multiplier=Decimal("2.0000"),
    )

    assert len(result.ingredients) == 1
    assert result.ingredients[0].required_quantity == Decimal("400.0000")
    assert result.ingredients[0].missing_quantity == Decimal("50.0000")
    assert result.shopping_requirements[0].quantity == Decimal("50.0000")


def test_unsafe_pantry_unit_conversion_fails_closed(db_session: Session) -> None:
    family = _persist_family(db_session, "Unsafe Unit Family")
    milk = _persist_food(db_session, family, key="food:milk", name="Milk")
    _add_stock(
        db_session,
        family,
        milk,
        stock_key="milk-liter",
        quantity="1.0000",
        unit="l",
    )

    if family.id is None:
        raise AssertionError("Family must be persisted.")
    with pytest.raises(PantryUnitConversionError, match="not safely convertible"):
        assess_food_pantry_stock(
            db_session,
            family_id=family.id,
            food_item=milk,
            required_quantity=Decimal("500.0000"),
            required_unit="g",
            as_of=AS_OF,
        )


def test_pantry_profiles_scale_recipe_candidate_against_recipe_yield(
    db_session: Session,
) -> None:
    family = _persist_family(db_session, "Candidate Pantry Family")
    snack = _persist_food(db_session, family, key="food:snack", name="Snack")
    flour = _persist_food(db_session, family, key="food:candidate-flour", name="Flour")
    _add_stock(
        db_session,
        family,
        snack,
        stock_key="snack-stock",
        quantity="200.0000",
        unit="g",
    )
    _add_stock(
        db_session,
        family,
        flour,
        stock_key="candidate-flour-stock",
        quantity="100.0000",
        unit="g",
    )

    food_composition = FoodCompositionSnapshot(
        food_item=snack,
        reference_quantity=Decimal("100.0000"),
        reference_unit="g",
        energy_kcal=Decimal("150.0000"),
        data_version="test-v1",
        source="test",
        effective_at=AS_OF - timedelta(days=1),
    )
    recipe = _persist_recipe(
        db_session,
        family,
        key="recipe:half-batch",
        ingredients=[(flour, "200.0000", "g")],
        yield_quantity="400.0000",
        yield_unit="g",
    )
    recipe_composition = RecipeCompositionSnapshot(
        recipe=recipe,
        reference_quantity=Decimal("100.0000"),
        reference_unit="g",
        energy_kcal=Decimal("200.0000"),
        composition_version="test-v1",
        calculation_version="test-v1",
        computed_at=AS_OF - timedelta(days=1),
    )
    db_session.add_all([food_composition, recipe_composition])
    db_session.flush()

    food_candidate = build_food_candidate(
        food_composition,
        quantity=Decimal("100.0000"),
        quantity_unit="g",
    )
    recipe_candidate = build_recipe_candidate(
        recipe_composition,
        quantity=Decimal("200.0000"),
        quantity_unit="g",
    )

    if family.id is None:
        raise AssertionError("Family must be persisted.")
    profiles = build_pantry_stock_practical_profiles(
        db_session,
        family_id=family.id,
        candidates=[food_candidate, recipe_candidate],
        as_of=AS_OF,
    )

    by_key = {profile.candidate_key: profile for profile in profiles}
    assert by_key["food:snack"].is_available is True
    assert by_key["recipe:half-batch"].is_available is True


def test_pantry_evaluation_rejects_catalog_item_from_another_family(
    db_session: Session,
) -> None:
    first = _persist_family(db_session, "First Pantry Family")
    second = _persist_family(db_session, "Second Pantry Family")
    food_item = _persist_food(
        db_session,
        first,
        key="food:first-family-pantry",
        name="First family food",
    )

    if second.id is None:
        raise AssertionError("Family must be persisted.")
    with pytest.raises(PantryPlanningError, match="another Family"):
        assess_food_pantry_stock(
            db_session,
            family_id=second.id,
            food_item=food_item,
            required_quantity=Decimal("100.0000"),
            required_unit="g",
            as_of=AS_OF,
        )
