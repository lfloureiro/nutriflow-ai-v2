from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.daily_health_state import DailyHealthState
from app.models.daily_nutrition_state import DailyNutritionState, DailyNutritionStateComponent
from app.models.family import Family
from app.models.nutrition_target import NutritionTarget
from app.models.person import Person


def test_daily_states_are_derived_versioned_snapshots(db_session: Session) -> None:
    family = Family(name="Daily State Test Family", timezone="Europe/Lisbon")
    person = Person(
        family=family,
        first_name="Daily",
        last_name="Tester",
        birth_date=date(1990, 1, 1),
        preferred_locale="pt-PT",
        timezone="Europe/Lisbon",
    )
    target = NutritionTarget(
        person=person,
        valid_from=date(2026, 8, 21),
        estimated_bmr_kcal=Decimal("1750.00"),
        bmr_method="mifflin_st_jeor",
        estimated_tdee_kcal=Decimal("2300.00"),
        tdee_method="baseline_activity",
        energy_min_kcal=Decimal("1800.00"),
        energy_max_kcal=Decimal("2000.00"),
        calculation_version="nutrition-v1",
        calculation_inputs={"weight_kg": 90.0},
        status="active",
        source="system",
    )

    health_state = DailyHealthState(
        person=person,
        state_date=date(2026, 8, 21),
        timezone="Europe/Lisbon",
        latest_weight_kg=Decimal("89.500"),
        weight_trend_7d_kg=Decimal("-0.400"),
        weight_trend_28d_kg=Decimal("-1.600"),
        steps=8500,
        active_energy_kcal=Decimal("520.00"),
        resting_energy_kcal=Decimal("1760.00"),
        estimated_expenditure_kcal=Decimal("2280.00"),
        sleep_duration_minutes=435,
        resting_heart_rate_bpm=Decimal("61.00"),
        hrv_ms=Decimal("46.00"),
        training_load=Decimal("32.5000"),
        confidence_score=Decimal("0.8700"),
        calculation_version="daily-health-v1",
        calculation_inputs={"measurement_count": 14},
        source_window_start_at=datetime(2026, 7, 25, tzinfo=UTC),
        source_window_end_at=datetime(2026, 8, 21, 23, 59, tzinfo=UTC),
    )
    nutrition_state = DailyNutritionState(
        person=person,
        nutrition_target=target,
        state_date=date(2026, 8, 21),
        timezone="Europe/Lisbon",
        energy_consumed_kcal=Decimal("1200.00"),
        energy_planned_kcal=Decimal("400.00"),
        energy_remaining_min_kcal=Decimal("200.00"),
        energy_remaining_max_kcal=Decimal("400.00"),
        adherence_score=Decimal("0.8200"),
        confidence_score=Decimal("0.9500"),
        calculation_version="daily-nutrition-v1",
        calculation_inputs={"meal_event_count": 3},
        components=[
            DailyNutritionStateComponent(
                target_type="nutrient",
                target_key="protein",
                consumed_value=Decimal("70.0000"),
                planned_value=Decimal("20.0000"),
                remaining_min=Decimal("20.0000"),
                remaining_max=Decimal("30.0000"),
                unit="g",
            ),
            DailyNutritionStateComponent(
                target_type="nutrient",
                target_key="fibre",
                consumed_value=Decimal("15.0000"),
                planned_value=Decimal("5.0000"),
                remaining_min=Decimal("10.0000"),
                unit="g",
            ),
        ],
    )

    db_session.add(person)
    db_session.flush()

    assert health_state.id is not None
    assert nutrition_state.id is not None
    assert nutrition_state.nutrition_target_id == target.id
    assert len(nutrition_state.components) == 2
    assert health_state.weight_trend_7d_kg == Decimal("-0.400")
    assert nutrition_state.energy_remaining_max_kcal == Decimal("400.00")

    revised_health_state = DailyHealthState(
        person_id=person.id,
        state_date=date(2026, 8, 21),
        timezone="Europe/Lisbon",
        latest_weight_kg=Decimal("89.500"),
        confidence_score=Decimal("0.9100"),
        calculation_version="daily-health-v2",
        calculation_inputs={"measurement_count": 16},
    )
    revised_nutrition_state = DailyNutritionState(
        person_id=person.id,
        nutrition_target_id=target.id,
        state_date=date(2026, 8, 21),
        timezone="Europe/Lisbon",
        energy_consumed_kcal=Decimal("1200.00"),
        energy_planned_kcal=Decimal("400.00"),
        energy_remaining_min_kcal=Decimal("200.00"),
        energy_remaining_max_kcal=Decimal("400.00"),
        calculation_version="daily-nutrition-v2",
        calculation_inputs={"meal_event_count": 3},
    )
    db_session.add_all([revised_health_state, revised_nutrition_state])
    db_session.flush()

    db_session.expire(person, ["daily_health_states", "daily_nutrition_states"])
    assert [state.calculation_version for state in person.daily_health_states] == [
        "daily-health-v1",
        "daily-health-v2",
    ]
    assert [state.calculation_version for state in person.daily_nutrition_states] == [
        "daily-nutrition-v1",
        "daily-nutrition-v2",
    ]
