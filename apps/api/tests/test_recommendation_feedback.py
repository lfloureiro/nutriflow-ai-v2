from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.models.daily_nutrition_state import DailyNutritionState
from app.models.family import Family
from app.models.food_adverse_reaction import FoodAdverseReaction
from app.models.food_catalog import FoodCompositionSnapshot, FoodItem, FoodNutrientComponent
from app.models.meal import MealEvent, MealParticipant, Serving
from app.models.person import Person
from app.services.meal_recommendation import build_food_candidate, recommend_meals
from app.services.recommendation_feedback import (
    RecommendationFeedbackError,
    persist_recommendation_run,
    record_recommendation_feedback,
)


def _food_candidate(
    *,
    key: str,
    name: str,
    energy: str,
    protein: str,
):
    food = FoodItem(
        catalog_key=key,
        name=name,
        food_kind="ingredient",
        source="test",
    )
    composition = FoodCompositionSnapshot(
        food_item=food,
        reference_quantity=Decimal("100.0000"),
        reference_unit="g",
        energy_kcal=Decimal(energy),
        data_version="test-v1",
        source="test",
        effective_at=datetime(2026, 8, 21, tzinfo=UTC),
        nutrients=[
            FoodNutrientComponent(
                nutrient_key="protein",
                value=Decimal(protein),
                unit="g",
            )
        ],
    )
    return build_food_candidate(
        composition,
        quantity=Decimal("100.0000"),
        quantity_unit="g",
    )


def _person_and_state() -> tuple[Family, Person, DailyNutritionState]:
    family = Family(name="Recommendation Feedback Family", timezone="Europe/Lisbon")
    person = Person(
        family=family,
        first_name="Feedback",
        last_name="Tester",
        birth_date=date(1990, 1, 1),
        preferred_locale="pt-PT",
        timezone="Europe/Lisbon",
    )
    state = DailyNutritionState(
        person=person,
        state_date=date(2026, 8, 21),
        timezone="Europe/Lisbon",
        energy_consumed_kcal=Decimal("900.00"),
        energy_planned_kcal=Decimal("300.00"),
        energy_remaining_min_kcal=Decimal("500.00"),
        energy_remaining_max_kcal=Decimal("800.00"),
        calculation_version="daily-nutrition-v1",
    )
    return family, person, state


def test_recommendation_run_persists_rank_exclusion_and_nutrition_snapshot(
    db_session: Session,
) -> None:
    family, person, state = _person_and_state()
    chicken = _food_candidate(
        key="food:chicken",
        name="Chicken",
        energy="550.0000",
        protein="45.0000",
    )
    peanut = _food_candidate(
        key="food:peanut",
        name="Peanut",
        energy="560.0000",
        protein="25.0000",
    )

    recommendation = recommend_meals(
        daily_state=state,
        candidates=[peanut, chicken],
        preferences=[],
        adverse_reactions=[
            FoodAdverseReaction(
                person=person,
                reaction_type="allergy",
                subject_type="ingredient",
                subject_key="food:peanut",
                severity="severe",
                is_mandatory=True,
                source="user",
            )
        ],
        constraints=[],
        planning_date=date(2026, 8, 21),
    )

    run = persist_recommendation_run(
        db_session,
        person=person,
        daily_state=state,
        recommendation=recommendation,
        planning_date=date(2026, 8, 21),
        meal_type="dinner",
        context={"request_source": "test"},
    )
    db_session.add(family)
    db_session.flush()

    assert run.id is not None
    assert run.engine_version == "meal-recommendation-v1"
    assert run.daily_nutrition_state_id == state.id
    assert len(run.options) == 2

    eligible = next(option for option in run.options if option.candidate_key == "food:chicken")
    excluded = next(option for option in run.options if option.candidate_key == "food:peanut")

    assert eligible.eligible is True
    assert eligible.rank == 1
    assert eligible.score is not None
    assert eligible.food_composition_snapshot_id == chicken.food_composition.id
    assert eligible.nutrition_snapshot == {
        "energy_kcal": "550.00",
        "nutrients": {"protein": {"value": "45.0000", "unit": "g"}},
    }
    assert eligible.score_breakdown is not None
    assert "energy" in eligible.score_breakdown

    assert excluded.eligible is False
    assert excluded.rank is None
    assert excluded.score is None
    assert excluded.exclusion_reasons == ["mandatory_reaction:ingredient:food:peanut"]
    assert person.meal_recommendation_runs[0] is run


def test_recommendation_feedback_records_modified_result_and_rejects_invalid_links(
    db_session: Session,
) -> None:
    family, person, state = _person_and_state()
    candidate = _food_candidate(
        key="food:chicken",
        name="Chicken",
        energy="550.0000",
        protein="45.0000",
    )
    recommendation = recommend_meals(
        daily_state=state,
        candidates=[candidate],
        preferences=[],
        adverse_reactions=[],
        constraints=[],
        planning_date=date(2026, 8, 21),
    )
    run = persist_recommendation_run(
        db_session,
        person=person,
        daily_state=state,
        recommendation=recommendation,
        planning_date=date(2026, 8, 21),
        meal_type="dinner",
    )

    meal = MealEvent(
        family=family,
        meal_type="dinner",
        title="Adjusted dinner",
        scheduled_at=datetime(2026, 8, 21, 19, 30, tzinfo=UTC),
        timezone="Europe/Lisbon",
    )
    participant = MealParticipant(meal_event=meal, person=person)
    serving = Serving(
        meal_participant=participant,
        food_item=candidate.food_item,
        item_type="food_item",
        item_key=candidate.key,
        item_name=candidate.name,
        quantity_planned=Decimal("120.0000"),
        quantity_unit="g",
        nutrition_source="catalog",
    )

    db_session.add(family)
    db_session.flush()

    option = run.options[0]
    feedback = record_recommendation_feedback(
        db_session,
        option=option,
        action="modified",
        resulting_serving=serving,
        metadata={"change": "larger_portion"},
    )
    db_session.flush()

    assert feedback.id is not None
    assert feedback.action == "modified"
    assert feedback.resulting_serving_id == serving.id
    assert feedback.feedback_metadata == {"change": "larger_portion"}
    assert option.feedback_events[0] is feedback

    with pytest.raises(RecommendationFeedbackError):
        record_recommendation_feedback(
            db_session,
            option=option,
            action="rejected",
            resulting_serving=serving,
        )
