import uuid
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.services.pantry_shopping import PantryShoppingError, _batch_multiplier


def _evidence():
    recipe_id, ingredient_id, food_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    ingredient = SimpleNamespace(
        id=ingredient_id, food_item_id=food_id, quantity=Decimal(450), unit="g"
    )
    recipe = SimpleNamespace(
        id=recipe_id,
        name="Six-serving pasta",
        ingredients=[ingredient],
        serving_count=None,
        yield_quantity=None,
        yield_unit=None,
    )
    snapshot = SimpleNamespace(
        id=uuid.uuid4(),
        recipe_id=recipe_id,
        reference_unit="serving",
        reference_quantity=Decimal(6),
        calculation_inputs={
            "ingredients": [
                {
                    "recipe_ingredient_id": str(ingredient_id),
                    "food_item_id": str(food_id),
                    "quantity": "450",
                    "unit": "g",
                }
            ],
            "serving_count_estimated": True,
        },
    )
    serving = SimpleNamespace(
        quantity_planned=Decimal(2),
        quantity_unit="serving",
        recipe_composition_snapshot=snapshot,
        meal_participant=SimpleNamespace(
            meal_event=SimpleNamespace(transformation_applications=[])
        ),
    )
    return recipe, snapshot, serving


def test_shopping_uses_frozen_batch_serving_basis_instead_of_losing_legacy_recipe():
    recipe, _, serving = _evidence()
    assert _batch_multiplier(serving, recipe) == Decimal(2) / Decimal(6)


def test_changed_ingredient_quantity_must_not_reuse_stale_batch_basis():
    recipe, _, serving = _evidence()
    recipe.ingredients[0].quantity = Decimal(900)
    with pytest.raises(PantryShoppingError):
        _batch_multiplier(serving, recipe)


def test_transformed_meal_uses_its_frozen_source_composition_basis():
    recipe, snapshot, serving = _evidence()
    serving.recipe_composition_snapshot = None
    serving.meal_participant.meal_event.transformation_applications = [
        SimpleNamespace(recipe_id=recipe.id, source_recipe_composition_snapshot=snapshot),
    ]
    assert _batch_multiplier(serving, recipe) == Decimal(2) / Decimal(6)


def test_snapshot_without_complete_ingredient_evidence_is_not_a_batch_conversion():
    recipe, snapshot, serving = _evidence()
    snapshot.calculation_inputs = {}
    with pytest.raises(PantryShoppingError):
        _batch_multiplier(serving, recipe)
