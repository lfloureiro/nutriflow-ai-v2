from datetime import date
from decimal import Decimal

from app.models.daily_nutrition_state import DailyNutritionState, DailyNutritionStateComponent
from app.models.nutrition_constraint import NutritionConstraint
from app.services.meal_recommendation import MealCandidate, recommend_meals
from app.services.serving_nutrition import NutritionSnapshot, NutrientSnapshot

PLANNING_DATE = date(2026, 8, 22)


def test_missing_mandatory_nutrient_data_excludes_only_unknown_candidate() -> None:
    sodium_state = DailyNutritionStateComponent(
        target_type="nutrient",
        target_key="sodium",
        consumed_value=Decimal("800.0000"),
        planned_value=Decimal("0.0000"),
        remaining_max=Decimal("200.0000"),
        unit="mg",
    )
    daily_state = DailyNutritionState(
        state_date=PLANNING_DATE,
        timezone="Europe/Lisbon",
        energy_consumed_kcal=Decimal("1000.00"),
        energy_planned_kcal=Decimal("0.00"),
        calculation_version="test-v1",
        components=[sodium_state],
    )
    sodium_limit = NutritionConstraint(
        constraint_type="nutrient_limit",
        target_type="nutrient",
        target_key="sodium",
        operator="max",
        value_max=Decimal("1000.0000"),
        unit="mg",
        severity="required",
        is_mandatory=True,
        source="doctor",
    )
    missing_sodium = MealCandidate(
        key="food:unknown-sodium",
        name="Unknown sodium food",
        kind="food_item",
        quantity=Decimal("100.0000"),
        quantity_unit="g",
        nutrition=NutritionSnapshot(
            energy_kcal=Decimal("300.00"),
            nutrients={},
        ),
        subjects=frozenset(),
    )
    known_zero_sodium = MealCandidate(
        key="food:known-zero-sodium",
        name="Known zero sodium food",
        kind="food_item",
        quantity=Decimal("100.0000"),
        quantity_unit="g",
        nutrition=NutritionSnapshot(
            energy_kcal=Decimal("300.00"),
            nutrients={
                "sodium": NutrientSnapshot(
                    value=Decimal("0.0000"),
                    unit="mg",
                )
            },
        ),
        subjects=frozenset(),
    )

    result = recommend_meals(
        daily_state=daily_state,
        candidates=[missing_sodium, known_zero_sodium],
        preferences=[],
        adverse_reactions=[],
        constraints=[sodium_limit],
        planning_date=PLANNING_DATE,
    )

    assert tuple(evaluation.candidate.key for evaluation in result.eligible) == (
        "food:known-zero-sodium",
    )
    missing_evaluation = next(
        evaluation
        for evaluation in result.evaluations
        if evaluation.candidate.key == "food:unknown-sodium"
    )
    assert missing_evaluation.eligible is False
    assert missing_evaluation.exclusion_reasons == (
        "mandatory_nutrient_data_missing:sodium",
    )
