from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.family import Family
from app.models.nutrition_goal import NutritionGoal
from app.models.nutrition_target import NutritionTarget, NutritionTargetComponent
from app.models.person import Person


def test_nutrition_targets_are_versioned_and_explainable(db_session: Session) -> None:
    family = Family(
        name="Nutrition Target Test Family",
        timezone="Europe/Lisbon",
    )
    person = Person(
        family=family,
        first_name="Target",
        last_name="Tester",
        birth_date=date(1990, 1, 1),
        preferred_locale="pt-PT",
        timezone="Europe/Lisbon",
    )
    goal = NutritionGoal(
        person=person,
        goal_type="weight_loss",
        target_weight_kg=Decimal("85.000"),
        target_rate_kg_per_week=Decimal("0.500"),
        start_date=date(2026, 1, 1),
    )

    db_session.add(person)
    db_session.flush()

    previous_target = NutritionTarget(
        person=person,
        nutrition_goal_id=goal.id,
        valid_from=date(2026, 1, 1),
        valid_until=date(2026, 6, 30),
        estimated_bmr_kcal=Decimal("1800.00"),
        bmr_method="mifflin_st_jeor",
        estimated_tdee_kcal=Decimal("2300.00"),
        tdee_method="baseline_activity",
        energy_min_kcal=Decimal("1800.00"),
        energy_max_kcal=Decimal("1900.00"),
        calculation_version="nutrition-target-v1",
        calculation_inputs={"weight_kg": 103.0, "activity_source": "baseline"},
        status="superseded",
    )
    NutritionTargetComponent(
        nutrition_target=previous_target,
        target_type="nutrient",
        target_key="protein",
        value_min=Decimal("120.0000"),
        value_max=Decimal("160.0000"),
        unit="g/day",
    )

    current_target = NutritionTarget(
        person=person,
        nutrition_goal_id=goal.id,
        valid_from=date(2026, 7, 1),
        estimated_bmr_kcal=Decimal("1785.00"),
        bmr_method="mifflin_st_jeor",
        estimated_tdee_kcal=Decimal("2250.00"),
        tdee_method="observed_activity_v1",
        energy_min_kcal=Decimal("1750.00"),
        energy_max_kcal=Decimal("1850.00"),
        calculation_version="nutrition-target-v2",
        calculation_inputs={
            "weight_kg": 99.2,
            "activity_source": "observed",
            "goal_type": "weight_loss",
        },
    )
    NutritionTargetComponent(
        nutrition_target=current_target,
        target_type="nutrient",
        target_key="protein",
        value_min=Decimal("130.0000"),
        value_max=Decimal("170.0000"),
        unit="g/day",
    )
    NutritionTargetComponent(
        nutrition_target=current_target,
        target_type="nutrient",
        target_key="fibre",
        value_target=Decimal("35.0000"),
        unit="g/day",
    )

    db_session.add_all([previous_target, current_target])
    db_session.flush()

    assert previous_target.id is not None
    assert current_target.id is not None
    assert current_target.status == "active"
    assert current_target.source == "system"
    assert current_target.nutrition_goal_id == goal.id

    db_session.expire(person, ["nutrition_targets"])
    targets = person.nutrition_targets

    assert len(targets) == 2
    assert targets[0].valid_from == date(2026, 1, 1)
    assert targets[0].status == "superseded"
    assert targets[1].valid_from == date(2026, 7, 1)
    assert targets[1].valid_until is None
    assert targets[1].calculation_version == "nutrition-target-v2"
    assert targets[1].energy_min_kcal == Decimal("1750.00")
    assert targets[1].energy_max_kcal == Decimal("1850.00")
    assert targets[1].calculation_inputs is not None
    assert targets[1].calculation_inputs["activity_source"] == "observed"

    components = {component.target_key: component for component in targets[1].components}
    assert components["protein"].value_min == Decimal("130.0000")
    assert components["protein"].value_max == Decimal("170.0000")
    assert components["fibre"].value_target == Decimal("35.0000")
