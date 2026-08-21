from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.models.family import Family
from app.models.food_catalog import FoodCompositionSnapshot, FoodItem, FoodNutrientComponent
from app.models.person import Person
from app.models.recommendation_feedback import MealRecommendationOption, MealRecommendationRun
from app.services.recommendation_planning import (
    RecommendationPlanningError,
    materialize_recommendation_option,
)


def _persisted_option(db_session: Session) -> MealRecommendationOption:
    family = Family(name="Planning Test Family", timezone="Europe/Lisbon")
    person = Person(
        family=family,
        first_name="Plan",
        last_name="Tester",
        birth_date=date(1990, 1, 1),
        preferred_locale="pt-PT",
        timezone="Europe/Lisbon",
    )
    food = FoodItem(
        family=family,
        catalog_key="family:planning:chicken",
        name="Chicken bowl",
        food_kind="dish",
        source="test",
    )
    composition = FoodCompositionSnapshot(
        food_item=food,
        reference_quantity=Decimal("100.0000"),
        reference_unit="g",
        energy_kcal=Decimal("200.0000"),
        data_version="test-v1",
        source="test",
        effective_at=datetime(2026, 8, 21, tzinfo=UTC),
        nutrients=[
            FoodNutrientComponent(
                nutrient_key="protein",
                value=Decimal("10.0000"),
                unit="g",
            )
        ],
    )
    run = MealRecommendationRun(
        person=person,
        planning_date=date(2026, 8, 22),
        meal_type="dinner",
        engine_version="meal-recommendation-v1",
    )
    option = MealRecommendationOption(
        recommendation_run=run,
        food_item=food,
        food_composition_snapshot=composition,
        candidate_key=food.catalog_key,
        candidate_name=food.name,
        candidate_kind="food_item",
        quantity=Decimal("250.0000"),
        quantity_unit="g",
        eligible=True,
        rank=1,
        score=Decimal("2.5000"),
        score_breakdown={"energy": "1.0000"},
        exclusion_reasons=[],
        explanation=["candidate_fits_remaining_energy"],
        candidate_subjects=[{"type": "dish", "key": food.catalog_key}],
        nutrition_snapshot={
            "energy_kcal": "500.00",
            "nutrients": {"protein": {"value": "25.0000", "unit": "g"}},
        },
    )

    db_session.add(family)
    db_session.flush()
    return option


def test_accepted_recommendation_creates_planned_meal_and_serving(db_session: Session) -> None:
    option = _persisted_option(db_session)

    result = materialize_recommendation_option(
        db_session,
        option=option,
        action="accepted",
        scheduled_at=datetime(2026, 8, 22, 19, 30, tzinfo=UTC),
        timezone="Europe/Lisbon",
        location="Home",
    )
    db_session.flush()

    assert result.feedback.action == "accepted"
    assert result.feedback.resulting_serving is result.serving
    assert result.meal_event.family is option.recommendation_run.person.family
    assert result.meal_event.meal_type == "dinner"
    assert result.meal_event.status == "planned"
    assert result.participant.person is option.recommendation_run.person
    assert result.participant.status == "planned"
    assert result.serving.quantity_planned == Decimal("250.0000")
    assert result.serving.energy_planned_kcal == Decimal("500.00")
    assert result.serving.food_composition_snapshot is option.food_composition_snapshot
    assert result.serving.nutrition_components[0].nutrient_key == "protein"
    assert result.serving.nutrition_components[0].planned_value == Decimal("25.0000")


def test_modified_recommendation_recalculates_nutrition_for_new_quantity(
    db_session: Session,
) -> None:
    option = _persisted_option(db_session)

    result = materialize_recommendation_option(
        db_session,
        option=option,
        action="modified",
        scheduled_at=datetime(2026, 8, 22, 20, 0, tzinfo=UTC),
        timezone="Europe/Lisbon",
        quantity=Decimal("150.0000"),
        feedback_metadata={"reason": "smaller_portion"},
    )
    db_session.flush()

    assert result.feedback.action == "modified"
    assert result.feedback.feedback_metadata == {"reason": "smaller_portion"}
    assert result.serving.quantity_planned == Decimal("150.0000")
    assert result.serving.energy_planned_kcal == Decimal("300.00")
    assert result.serving.nutrition_components[0].planned_value == Decimal("15.0000")


def test_accepted_action_rejects_quantity_changes(db_session: Session) -> None:
    option = _persisted_option(db_session)

    with pytest.raises(RecommendationPlanningError, match="action='modified'"):
        materialize_recommendation_option(
            db_session,
            option=option,
            action="accepted",
            scheduled_at=datetime(2026, 8, 22, 19, 30, tzinfo=UTC),
            timezone="Europe/Lisbon",
            quantity=Decimal("150.0000"),
        )
