from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.family import Family
from app.models.nutrition_constraint import NutritionConstraint
from app.models.person import Person
from app.schemas.nutrition_plan import (
    NutritionPlanCreate,
    NutritionPlanGuidelineCreate,
    NutritionPlanRuleCreate,
    NutritionPlanUpdate,
    NutritionPlanVersionCreate,
)
from app.services.nutrition_plan import (
    add_nutrition_plan_guideline,
    add_nutrition_plan_rule,
    compile_effective_nutrition_plan,
    create_nutrition_plan,
    create_nutrition_plan_version,
    get_nutrition_plan,
    update_nutrition_plan,
)


def _person(db_session: Session) -> Person:
    family = Family(name="Plan Test Family", timezone="Europe/Lisbon")
    person = Person(
        family=family,
        first_name="Plan",
        last_name="Tester",
        birth_date=date(1980, 1, 1),
        preferred_locale="pt-PT",
        timezone="Europe/Lisbon",
    )
    db_session.add(person)
    db_session.commit()
    return person


def test_effective_plan_scopes_rules_and_surfaces_conflicts(db_session: Session) -> None:
    person = _person(db_session)
    plan = create_nutrition_plan(
        db_session,
        person=person,
        data=NutritionPlanCreate(
            title="Professional lunch plan",
            source_type="nutritionist",
            source_name="Dr. Example",
            source_reference="plan-2026-09",
            status="draft",
            valid_from=date(2026, 9, 1),
        ),
    )

    protein_minimum = NutritionConstraint(
        person_id=person.id,
        constraint_type="nutrient_target",
        target_type="nutrient",
        target_key="protein",
        operator="min",
        value_min=Decimal("50"),
        unit="g",
        severity="required",
        is_mandatory=True,
        source="nutritionist",
        source_name="Dr. Example",
    )
    protein_maximum = NutritionConstraint(
        person_id=person.id,
        constraint_type="nutrient_limit",
        target_type="nutrient",
        target_key="protein",
        operator="max",
        value_max=Decimal("40"),
        unit="g",
        severity="required",
        is_mandatory=True,
        source="nutritionist",
        source_name="Dr. Example",
    )
    db_session.add_all([protein_minimum, protein_maximum])
    db_session.commit()

    for constraint in (protein_minimum, protein_maximum):
        add_nutrition_plan_rule(
            db_session,
            plan=plan,
            data=NutritionPlanRuleCreate(
                rule_kind="constraint",
                reference_id=constraint.id,
                meal_type="lunch",
                source_statement="Protein prescription for lunch",
            ),
        )

    add_nutrition_plan_guideline(
        db_session,
        plan=plan,
        data=NutritionPlanGuidelineCreate(
            guideline_type="frequency",
            target_type="food_group",
            target_key="fish",
            description="Eat fish at least three times per week",
            period="week",
            minimum_occurrences=3,
            source_statement="Fish >= 3 meals/week",
        ),
    )
    update_nutrition_plan(
        db_session,
        plan=plan,
        data=NutritionPlanUpdate(status="active"),
    )

    lunch = compile_effective_nutrition_plan(
        db_session,
        person_id=person.id,
        on_date=date(2026, 9, 15),
        meal_type="lunch",
    )
    assert len(lunch.active_plans) == 1
    assert len(lunch.numeric_rules) == 2
    assert {rule.target_key for rule in lunch.numeric_rules} == {"protein"}
    assert all(rule.is_mandatory for rule in lunch.numeric_rules)
    assert all(rule.source.plan_source_type == "nutritionist" for rule in lunch.numeric_rules)
    assert len(lunch.guidelines) == 1
    assert lunch.guidelines[0].target_key == "fish"
    assert len(lunch.conflicts) == 1
    assert lunch.conflicts[0].severity == "mandatory"
    assert lunch.conflicts[0].target_key == "protein"

    breakfast = compile_effective_nutrition_plan(
        db_session,
        person_id=person.id,
        on_date=date(2026, 9, 15),
        meal_type="breakfast",
    )
    assert breakfast.numeric_rules == []
    assert len(breakfast.guidelines) == 1


def test_new_version_clones_content_and_supersedes_on_activation(db_session: Session) -> None:
    person = _person(db_session)
    first = create_nutrition_plan(
        db_session,
        person=person,
        data=NutritionPlanCreate(
            title="Versioned plan",
            source_type="clinician",
            source_name="Clinic",
            status="draft",
            valid_from=date(2026, 9, 1),
        ),
    )
    add_nutrition_plan_guideline(
        db_session,
        plan=first,
        data=NutritionPlanGuidelineCreate(
            guideline_type="qualitative",
            target_type="food_group",
            target_key="vegetables",
            description="Prefer vegetables at lunch",
            meal_type="lunch",
        ),
    )
    first = update_nutrition_plan(
        db_session,
        plan=first,
        data=NutritionPlanUpdate(status="active"),
    )

    second = create_nutrition_plan_version(
        db_session,
        base_plan=first,
        data=NutritionPlanVersionCreate(
            title="Versioned plan - revised",
            valid_from=date(2026, 9, 15),
        ),
    )
    assert second.lineage_id == first.lineage_id
    assert second.version == 2
    assert second.supersedes_plan_id == first.id
    assert second.status == "draft"
    assert len(second.guidelines) == 1

    first_before_activation = get_nutrition_plan(
        db_session,
        person_id=person.id,
        plan_id=first.id,
    )
    assert first_before_activation is not None
    assert first_before_activation.status == "active"

    second = update_nutrition_plan(
        db_session,
        plan=second,
        data=NutritionPlanUpdate(status="active"),
    )
    first_after_activation = get_nutrition_plan(
        db_session,
        person_id=person.id,
        plan_id=first.id,
    )
    assert second.status == "active"
    assert first_after_activation is not None
    assert first_after_activation.status == "superseded"

    effective = compile_effective_nutrition_plan(
        db_session,
        person_id=person.id,
        on_date=date(2026, 9, 15),
        meal_type="lunch",
    )
    assert [plan.id for plan in effective.active_plans] == [second.id]
    assert len(effective.guidelines) == 1
    assert effective.guidelines[0].source.plan_id == second.id
