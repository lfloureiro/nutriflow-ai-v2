from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.legacy_v1_loureiro_seed import (
    LOUREIRO_FAMILY_ID,
    seed_loureiro_v1_snapshot,
)
from app.models.family import Family
from app.models.food_catalog import FoodItem, Recipe, RecipeIngredient
from app.models.food_preference import FoodPreference
from app.models.person import Person


def _snapshot() -> dict[str, object]:
    return {
        "data": {
            "households": [{"id": 1, "name": "Família Loureiro"}],
            "family_members": [
                {"id": 1, "name": "Luis", "household_id": 1},
                {"id": 2, "name": "Patricia", "household_id": 1},
                {"id": 3, "name": "Tiago", "household_id": 1},
                {"id": 4, "name": "Diogo", "household_id": 1},
            ],
            "ingredients": [
                {"id": 10, "name": "Arroz"},
                {"id": 20, "name": "Frango"},
                {"id": 30, "name": "Papel higiénico"},
            ],
            "recipes": [
                {"id": 1, "name": "Frango com arroz", "description": "Teste"},
                {"id": 2, "name": "Arroz simples", "description": None},
            ],
            "recipe_ingredients": [
                {
                    "id": 101,
                    "recipe_id": 1,
                    "ingredient_id": 20,
                    "quantity": "400",
                    "unit": "g",
                },
                {
                    "id": 102,
                    "recipe_id": 1,
                    "ingredient_id": 10,
                    "quantity": None,
                    "unit": None,
                },
                {
                    "id": 103,
                    "recipe_id": 2,
                    "ingredient_id": 10,
                    "quantity": "200",
                    "unit": "g",
                },
            ],
            "recipe_preferences": [
                {
                    "id": 1,
                    "household_id": 1,
                    "family_member_id": 1,
                    "recipe_id": 1,
                    "rating": 5,
                    "note": "Muito bom",
                    "updated_at": "2026-04-25T21:00:00",
                },
                {
                    "id": 2,
                    "household_id": 1,
                    "family_member_id": 4,
                    "recipe_id": 1,
                    "rating": 0,
                    "note": "Não gosto",
                    "updated_at": "2026-04-25T21:05:00",
                },
            ],
        }
    }


def test_loureiro_import_preserves_family_recipes_and_zero_rating(
    db_session: Session,
) -> None:
    first = seed_loureiro_v1_snapshot(db_session, snapshot=_snapshot())
    second = seed_loureiro_v1_snapshot(db_session, snapshot=_snapshot())
    db_session.flush()

    assert first == second
    assert first.family_id == LOUREIRO_FAMILY_ID
    assert first.member_count == 4
    assert first.ingredient_count == 2
    assert first.recipe_count == 2
    assert first.rating_count == 2

    family = db_session.get(Family, LOUREIRO_FAMILY_ID)
    assert family is not None
    assert family.name == "Família Loureiro"

    people = list(
        db_session.scalars(
            select(Person)
            .where(Person.family_id == LOUREIRO_FAMILY_ID)
            .order_by(Person.first_name)
        ).all()
    )
    assert {person.first_name for person in people} == {
        "Luis",
        "Patricia",
        "Tiago",
        "Diogo",
    }

    recipe = db_session.scalar(select(Recipe).where(Recipe.recipe_key == "legacy-v1:recipe:1"))
    assert recipe is not None
    assert recipe.family_id is None
    assert recipe.name == "Frango com arroz"

    ingredients = list(
        db_session.scalars(
            select(RecipeIngredient)
            .where(RecipeIngredient.recipe_id == recipe.id)
            .order_by(RecipeIngredient.sort_order)
        ).all()
    )
    assert len(ingredients) == 2
    assert ingredients[0].quantity == Decimal("400.0000")
    assert ingredients[1].quantity == Decimal("1.0000")
    assert ingredients[1].unit == "qb"
    assert ingredients[1].notes is not None
    assert "não especificada" in ingredients[1].notes

    assert db_session.scalar(select(func.count()).select_from(FoodItem)) == 2
    assert db_session.scalar(select(func.count()).select_from(Recipe)) == 2
    assert db_session.scalar(select(func.count()).select_from(RecipeIngredient)) == 3
    assert db_session.scalar(select(func.count()).select_from(FoodPreference)) == 2

    zero_rating = db_session.scalar(
        select(FoodPreference).where(FoodPreference.intensity == 0)
    )
    assert zero_rating is not None
    assert zero_rating.notes == "Não gosto"
    assert zero_rating.source == "legacy-v1"
