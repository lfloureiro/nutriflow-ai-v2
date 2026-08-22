from datetime import UTC, date, datetime
from decimal import Decimal

from app.models.daily_nutrition_state import DailyNutritionState
from app.models.food_catalog import Recipe, RecipeCompositionSnapshot
from app.models.food_preference import FoodPreference
from app.services.meal_recommendation import build_recipe_candidate, recommend_meals


def _candidate(key: str, name: str):
    recipe = Recipe(recipe_key=key, name=name, source="test")
    snapshot = RecipeCompositionSnapshot(
        recipe=recipe,
        reference_quantity=Decimal(1),
        reference_unit="serving",
        energy_kcal=Decimal(500),
        composition_version="test-v1",
        calculation_version="test",
        computed_at=datetime(2026, 8, 22, tzinfo=UTC),
    )
    return build_recipe_candidate(snapshot, quantity=Decimal(1), quantity_unit="serving")


def test_five_star_recipe_ranks_above_identical_one_star_recipe() -> None:
    favorite = _candidate("recipe:favorite", "Favorite")
    disliked = _candidate("recipe:disliked", "Disliked")
    state = DailyNutritionState(
        state_date=date(2026, 8, 22),
        timezone="Europe/Lisbon",
        energy_consumed_kcal=Decimal(1000),
        energy_planned_kcal=Decimal(0),
        energy_remaining_min_kcal=Decimal(400),
        energy_remaining_max_kcal=Decimal(700),
        calculation_version="test",
    )

    result = recommend_meals(
        daily_state=state,
        candidates=[disliked, favorite],
        preferences=[
            FoodPreference(
                subject_type="recipe",
                subject_key="recipe:favorite",
                preference_type="rating",
                intensity=5,
                source="user",
            ),
            FoodPreference(
                subject_type="recipe",
                subject_key="recipe:disliked",
                preference_type="rating",
                intensity=1,
                source="user",
            ),
        ],
        adverse_reactions=[],
        constraints=[],
        planning_date=date(2026, 8, 22),
    )

    assert result.eligible[0].candidate.key == "recipe:favorite"
    assert result.eligible[0].score_breakdown["preferences"] == Decimal(1)
    assert "rated:recipe:recipe:favorite:5" in result.eligible[0].explanation
    assert result.eligible[1].score_breakdown["preferences"] == Decimal(-1)


def test_three_star_rating_is_neutral() -> None:
    neutral = _candidate("recipe:neutral", "Neutral")
    state = DailyNutritionState(
        state_date=date(2026, 8, 22),
        timezone="Europe/Lisbon",
        energy_consumed_kcal=Decimal(0),
        energy_planned_kcal=Decimal(0),
        calculation_version="test",
    )
    result = recommend_meals(
        daily_state=state,
        candidates=[neutral],
        preferences=[
            FoodPreference(
                subject_type="recipe",
                subject_key="recipe:neutral",
                preference_type="rating",
                intensity=3,
                source="user",
            )
        ],
        adverse_reactions=[],
        constraints=[],
        planning_date=date(2026, 8, 22),
    )
    assert result.eligible[0].score_breakdown["preferences"] == Decimal(0)
