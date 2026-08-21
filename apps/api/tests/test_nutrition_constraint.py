from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.family import Family
from app.models.nutrition_constraint import NutritionConstraint
from app.models.person import Person


def test_person_nutrition_constraints(db_session: Session) -> None:
    family = Family(
        name="Constraint Test Family",
        timezone="Europe/Lisbon",
    )

    person = Person(
        family=family,
        first_name="Constraint",
        last_name="Tester",
        birth_date=date(1990, 1, 1),
        preferred_locale="pt-PT",
        timezone="Europe/Lisbon",
    )

    sodium_limit = NutritionConstraint(
        person=person,
        constraint_type="nutrient_limit",
        target_type="nutrient",
        target_key="sodium",
        operator="max",
        value_max=Decimal("2000.0000"),
        unit="mg",
        severity="required",
        is_mandatory=True,
        source="nutritionist",
        source_name="Test Nutritionist",
        start_date=date(2026, 8, 21),
        notes="Professional sodium limit",
    )

    protein_minimum = NutritionConstraint(
        person=person,
        constraint_type="nutrient_target",
        target_type="nutrient",
        target_key="protein",
        operator="min",
        value_min=Decimal("120.0000"),
        unit="g",
        severity="advisory",
        is_mandatory=False,
        source="user",
    )

    db_session.add(person)
    db_session.flush()

    assert person.id is not None
    assert sodium_limit.id is not None
    assert protein_minimum.id is not None

    assert sodium_limit.person_id == person.id
    assert sodium_limit.is_mandatory is True
    assert sodium_limit.source == "nutritionist"
    assert sodium_limit.value_max == Decimal("2000.0000")

    assert protein_minimum.is_mandatory is False
    assert protein_minimum.source == "user"
    assert protein_minimum.value_min == Decimal("120.0000")

    db_session.expire(person, ["nutrition_constraints"])

    constraints = person.nutrition_constraints

    assert len(constraints) == 2

    targets = {constraint.target_key: constraint for constraint in constraints}

    assert targets["sodium"].operator == "max"
    assert targets["sodium"].severity == "required"
    assert targets["sodium"].is_mandatory is True

    assert targets["protein"].operator == "min"
    assert targets["protein"].severity == "advisory"
