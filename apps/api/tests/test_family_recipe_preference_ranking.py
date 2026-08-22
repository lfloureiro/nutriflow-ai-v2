from datetime import UTC, date, datetime
from decimal import Decimal

from app.models.daily_nutrition_state import DailyNutritionState
from app.models.food_catalog import Recipe, RecipeCompositionSnapshot
from app.services.meal_recommendation import build_recipe_candidate
from app.services.recommendation_practical_context import (
    PracticalMealContext,
    recommend_meals_with_practical_context,
)


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


def test_family_rating_is_secondary_and_reranks_equal_recipes() -> None:
    liked = _candidate("recipe:liked", "Liked")
    neutral = _candidate("recipe:neutral", "Neutral")
    state = DailyNutritionState(
        state_date=date(2026, 8, 22),
        timezone="Europe/Lisbon",
        energy_consumed_kcal=Decimal(1000),
        energy_planned_kcal=Decimal(0),
        energy_remaining_min_kcal=Decimal(400),
        energy_remaining_max_kcal=Decimal(700),
        calculation_version="test",
    )

    result = recommend_meals_with_practical_context(
        daily_state=state,
        candidates=[neutral, liked],
        preferences=[],
        adverse_reactions=[],
        constraints=[],
        planning_date=date(2026, 8, 22),
        practical_context=PracticalMealContext(
            scheduled_at=datetime(2026, 8, 22, 12, 0, tzinfo=UTC)
        ),
        family_recipe_ratings={"recipe:liked": Decimal(5)},
    )

    assert result.eligible[0].candidate.key == "recipe:liked"
    assert result.eligible[0].score_breakdown["family_preferences"] == Decimal("0.5")
    assert result.eligible[1].score_breakdown["family_preferences"] == Decimal(0)


def test_family_rating_does_not_restore_mandatory_exclusion() -> None:
    # Mandatory exclusions are handled before the family preference adjustment;
    # this regression guard ensures the adjustment only touches eligible candidates.
    excluded = _candidate("recipe:excluded", "Excluded")
    state = DailyNutritionState(
        state_date=date(2026, 8, 22),
        timezone="Europe/Lisbon",
        energy_consumed_kcal=Decimal(0),
        energy_planned_kcal=Decimal(0),
        calculation_version="test",
    )
    from app.models.nutrition_constraint import NutritionConstraint

    result = recommend_meals_with_practical_context(
        daily_state=state,
        candidates=[excluded],
        preferences=[],
        adverse_reactions=[],
        constraints=[
            NutritionConstraint(
                constraint_type="exclude",
                target_type="recipe",
                target_key="recipe:excluded",
                operator="exclude",
                severity="required",
                is_mandatory=True,
                source="test",
            )
        ],
        planning_date=date(2026, 8, 22),
        practical_context=PracticalMealContext(
            scheduled_at=datetime(2026, 8, 22, 12, 0, tzinfo=UTC)
        ),
        family_recipe_ratings={"recipe:excluded": Decimal(5)},
    )

    assert result.evaluations[0].eligible is False
    assert result.evaluations[0].score is None
