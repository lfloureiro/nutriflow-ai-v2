import uuid
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.demo_seed import DEMO_PERSON_ID
from app.models.nutrition_constraint import NutritionConstraint
from app.models.nutrition_plan import NutritionPlan, NutritionPlanGuideline, NutritionPlanRule
from app.models.person import Person

PLAN_ID = uuid.UUID("9cbbfcd2-327e-4ee1-88ea-7dddf12e2491")
PLAN_LINEAGE_ID = uuid.UUID("f6b5ce58-a877-4d08-86e1-40185265d747")
PROTEIN_CONSTRAINT_ID = uuid.UUID("5cc1328d-ad5b-498d-98ea-a9fc36fcbca4")
FIBER_CONSTRAINT_ID = uuid.UUID("e7e174d3-6485-458d-b565-b5fabfa901f3")
PROTEIN_RULE_ID = uuid.UUID("7380c2cf-31ae-4a78-a0e6-c10d0280b525")
FIBER_RULE_ID = uuid.UUID("6b3987af-8b7d-46aa-8867-3c0cbd1f8a2d")
GUIDELINE_ID = uuid.UUID("c4e7a177-3dbb-44f1-b3bc-09f8521416ac")
SOURCE_REFERENCE = "development-plan-fit-demo-v1"


@dataclass(frozen=True)
class DevelopmentPlanFitSeedResult:
    person_id: uuid.UUID
    plan_id: uuid.UUID
    rule_count: int
    guideline_count: int


def _constraint(
    session: Session,
    *,
    constraint_id: uuid.UUID,
    person: Person,
    target_key: str,
    minimum: Decimal,
    mandatory: bool,
) -> NutritionConstraint:
    constraint = session.get(NutritionConstraint, constraint_id)
    if constraint is None:
        constraint = NutritionConstraint(id=constraint_id, person_id=person.id)
        session.add(constraint)
    constraint.person_id = person.id
    constraint.constraint_type = "meal_target"
    constraint.target_type = "nutrient"
    constraint.target_key = target_key
    constraint.operator = "min"
    constraint.value_min = minimum
    constraint.value_max = None
    constraint.unit = "g"
    constraint.severity = "required" if mandatory else "advisory"
    constraint.is_mandatory = mandatory
    constraint.source = "nutritionist"
    constraint.source_name = "NutriFlow demo nutritionist"
    constraint.source_reference = SOURCE_REFERENCE
    constraint.start_date = date(2026, 1, 1)
    constraint.end_date = None
    constraint.notes = "Synthetic development-only nutrition-plan rule."
    return constraint


def seed_development_plan_fit(
    session: Session,
    *,
    person_id: uuid.UUID = DEMO_PERSON_ID,
) -> DevelopmentPlanFitSeedResult:
    person = session.get(Person, person_id)
    if person is None:
        raise ValueError("Development Plan-Fit seed requires the demo Person first.")

    plan = session.get(NutritionPlan, PLAN_ID)
    if plan is None:
        plan = NutritionPlan(id=PLAN_ID, person_id=person.id, lineage_id=PLAN_LINEAGE_ID)
        session.add(plan)
    plan.person_id = person.id
    plan.lineage_id = PLAN_LINEAGE_ID
    plan.version = 1
    plan.supersedes_plan_id = None
    plan.title = "Plano alimentar demo — pequeno-almoço"
    plan.source_type = "nutritionist"
    plan.source_name = "NutriFlow demo nutritionist"
    plan.source_reference = SOURCE_REFERENCE
    plan.original_text = (
        "Pequeno-almoço: pelo menos 15 g de proteína.\n"
        "Pequeno-almoço: pelo menos 6 g de fibra.\n"
        "Preferir fruta inteira ao pequeno-almoço."
    )
    plan.status = "active"
    plan.valid_from = date(2026, 1, 1)
    plan.valid_until = None
    session.flush()

    protein = _constraint(
        session,
        constraint_id=PROTEIN_CONSTRAINT_ID,
        person=person,
        target_key="protein",
        minimum=Decimal("15.0000"),
        mandatory=True,
    )
    fiber = _constraint(
        session,
        constraint_id=FIBER_CONSTRAINT_ID,
        person=person,
        target_key="fiber",
        minimum=Decimal("6.0000"),
        mandatory=False,
    )
    session.flush()

    for rule_id, constraint, priority, statement in (
        (
            PROTEIN_RULE_ID,
            protein,
            120,
            "Pequeno-almoço: pelo menos 15 g de proteína.",
        ),
        (
            FIBER_RULE_ID,
            fiber,
            100,
            "Pequeno-almoço: pelo menos 6 g de fibra.",
        ),
    ):
        rule = session.get(NutritionPlanRule, rule_id)
        if rule is None:
            rule = NutritionPlanRule(id=rule_id, nutrition_plan_id=plan.id)
            session.add(rule)
        rule.nutrition_plan_id = plan.id
        rule.rule_kind = "constraint"
        rule.nutrition_constraint_id = constraint.id
        rule.nutrition_target_component_id = None
        rule.nutrition_goal_id = None
        rule.meal_type = "breakfast"
        rule.priority = priority
        rule.valid_from = None
        rule.valid_until = None
        rule.source_statement = statement
        rule.applies_outside_plan = False

    guideline = session.get(NutritionPlanGuideline, GUIDELINE_ID)
    if guideline is None:
        guideline = NutritionPlanGuideline(id=GUIDELINE_ID, nutrition_plan_id=plan.id)
        session.add(guideline)
    guideline.nutrition_plan_id = plan.id
    guideline.guideline_type = "qualitative"
    guideline.target_type = "food_category"
    guideline.target_key = "fruit"
    guideline.description = "Preferir fruta inteira ao pequeno-almoço."
    guideline.meal_type = "breakfast"
    guideline.period = None
    guideline.minimum_occurrences = None
    guideline.maximum_occurrences = None
    guideline.severity = "advisory"
    guideline.is_mandatory = False
    guideline.confirmation_status = "confirmed"
    guideline.priority = 90
    guideline.valid_from = None
    guideline.valid_until = None
    guideline.source_statement = "Preferir fruta inteira ao pequeno-almoço."

    session.flush()
    return DevelopmentPlanFitSeedResult(
        person_id=person.id,
        plan_id=plan.id,
        rule_count=2,
        guideline_count=1,
    )
