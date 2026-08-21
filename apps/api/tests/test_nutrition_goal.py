from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.family import Family
from app.models.nutrition_goal import NutritionGoal
from app.models.person import Person


def test_person_nutrition_goal_history(db_session: Session) -> None:
    family = Family(
        name="Goal Test Family",
        timezone="Europe/Lisbon",
    )

    person = Person(
        family=family,
        first_name="Goal",
        last_name="Tester",
        birth_date=date(1990, 1, 1),
        preferred_locale="pt-PT",
        timezone="Europe/Lisbon",
    )

    previous_goal = NutritionGoal(
        person=person,
        goal_type="weight_maintenance",
        target_weight_kg=Decimal("100.000"),
        start_date=date(2026, 1, 1),
        target_date=date(2026, 6, 30),
        status="completed",
        source="user",
    )

    current_goal = NutritionGoal(
        person=person,
        goal_type="weight_loss",
        target_weight_kg=Decimal("90.000"),
        target_rate_kg_per_week=Decimal("0.500"),
        start_date=date(2026, 8, 21),
        target_date=date(2027, 2, 28),
        notes="Initial weight-loss goal",
    )

    db_session.add(person)
    db_session.flush()

    assert person.id is not None
    assert previous_goal.id is not None
    assert current_goal.id is not None

    assert previous_goal.person_id == person.id
    assert current_goal.person_id == person.id

    assert previous_goal.status == "completed"
    assert current_goal.status == "active"
    assert current_goal.source == "user"

    assert current_goal.target_weight_kg == Decimal("90.000")
    assert current_goal.target_rate_kg_per_week == Decimal("0.500")

    db_session.expire(person, ["nutrition_goals"])

    goals = person.nutrition_goals

    assert len(goals) == 2

    assert goals[0].goal_type == "weight_maintenance"
    assert goals[0].start_date == date(2026, 1, 1)
    assert goals[0].status == "completed"

    assert goals[1].goal_type == "weight_loss"
    assert goals[1].start_date == date(2026, 8, 21)
    assert goals[1].status == "active"
