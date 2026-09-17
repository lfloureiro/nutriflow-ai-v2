import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from app.schemas.meal_plan_fit import (
    MealPlanFitCandidateRead,
    MealPlanFitRead,
    MealPlanFitRuleRead,
)
from app.schemas.meal_recommendation import RecommendationNutritionRead
from app.schemas.nutrition_plan import (
    EffectiveNutritionNumericRuleRead,
    EffectiveNutritionPlanConflictRead,
    EffectiveNutritionPlanRead,
    EffectiveNutritionPlanSourceRead,
    NutritionPlanRead,
)


def _plan() -> NutritionPlanRead:
    now = datetime(2026, 9, 17, 12, 0, tzinfo=UTC)
    plan_id = uuid.uuid4()
    return NutritionPlanRead(
        id=plan_id,
        person_id=uuid.uuid4(),
        lineage_id=uuid.uuid4(),
        version=1,
        supersedes_plan_id=None,
        title="Nutritionist plan",
        source_type="nutritionist",
        source_name="Nutritionist Example",
        source_reference="document:plan",
        original_text=None,
        status="active",
        valid_from=date(2026, 9, 1),
        valid_until=None,
        created_at=now,
        updated_at=now,
    )


def _plan_source(plan: NutritionPlanRead) -> EffectiveNutritionPlanSourceRead:
    return EffectiveNutritionPlanSourceRead(
        plan_id=plan.id,
        plan_title=plan.title,
        plan_source_type=plan.source_type,
        source_name=plan.source_name,
        source_reference=plan.source_reference,
        rule_source="nutritionist",
    )


def _standalone_source() -> EffectiveNutritionPlanSourceRead:
    return EffectiveNutritionPlanSourceRead(
        plan_id=None,
        plan_title=None,
        plan_source_type=None,
        source_name="Clinic",
        source_reference=None,
        rule_source="clinician",
    )


def _rule(
    *,
    source: EffectiveNutritionPlanSourceRead,
    rule_id: str = "plan-rule:protein",
) -> EffectiveNutritionNumericRuleRead:
    return EffectiveNutritionNumericRuleRead(
        id=rule_id,
        rule_kind="constraint",
        target_type="nutrient",
        target_key="protein",
        operator="min",
        value_min=Decimal(25),
        value_max=None,
        value_target=None,
        unit="g",
        severity="required",
        is_mandatory=True,
        priority=10600,
        meal_type="lunch",
        source=source,
    )


def _effective(
    *,
    plans: list[NutritionPlanRead],
    rules: list[EffectiveNutritionNumericRuleRead] | None = None,
    conflicts: list[EffectiveNutritionPlanConflictRead] | None = None,
) -> EffectiveNutritionPlanRead:
    person_id = plans[0].person_id if plans else uuid.uuid4()
    return EffectiveNutritionPlanRead(
        person_id=person_id,
        effective_date=date(2026, 9, 17),
        meal_type="lunch",
        active_plans=plans,
        numeric_rules=rules or [],
        goals=[],
        guidelines=[],
        conflicts=conflicts or [],
    )


def test_effective_plan_authority_distinguishes_absent_partial_active_and_conflict() -> None:
    no_plan = _effective(plans=[])
    assert no_plan.nutrition_plan_authority.state == "no_active_plan"

    plan = _plan()
    partial = _effective(plans=[plan])
    assert partial.nutrition_plan_authority.state == "partial_plan_coverage"

    active = _effective(plans=[plan], rules=[_rule(source=_plan_source(plan))])
    assert active.nutrition_plan_authority.state == "active_plan"
    assert active.nutrition_plan_authority.plan_rule_ids == ["plan-rule:protein"]
    assert active.nutrition_plan_authority.active_plans[0].source_name == "Nutritionist Example"

    conflict = _effective(
        plans=[plan],
        rules=[_rule(source=_plan_source(plan))],
        conflicts=[
            EffectiveNutritionPlanConflictRead(
                target_type="nutrient",
                target_key="protein",
                unit="g",
                severity="mandatory",
                rule_ids=["plan-rule:min", "plan-rule:max"],
                message="Conflicting protein guidance.",
            )
        ],
    )
    assert conflict.nutrition_plan_authority.state == "plan_conflict"

    dumped = active.model_dump(mode="json")
    assert dumped["nutrition_plan_authority"]["state"] == "active_plan"
    assert dumped["nutrition_plan_authority"]["active_plans"][0]["title"] == "Nutritionist plan"


def test_meal_plan_fit_marks_unknown_plan_evidence_as_partial_coverage() -> None:
    plan = _plan()
    source = _plan_source(plan)
    fit = MealPlanFitRead(
        person_id=plan.person_id,
        planning_date=date(2026, 9, 17),
        meal_type="lunch",
        daily_nutrition_state_id=None,
        candidate=MealPlanFitCandidateRead(
            key="recipe:test",
            name="Test recipe",
            kind="recipe",
            quantity=Decimal(1),
            quantity_unit="serving",
            nutrition=RecommendationNutritionRead(energy_kcal=None, nutrients={}),
        ),
        eligible=False,
        status="unknown",
        fit_score=None,
        active_plans=[plan],
        conflicts=[],
        safety_issues=[],
        rule_results=[
            MealPlanFitRuleRead(
                rule_id="plan-rule:protein",
                target_type="nutrient",
                target_key="protein",
                operator="min",
                scope="meal",
                status="unknown",
                is_mandatory=True,
                priority=10600,
                observed_value=None,
                observed_unit=None,
                projected_daily_value=None,
                target_min=Decimal(25),
                target_max=None,
                target_value=None,
                target_unit="g",
                score=None,
                explanation="Candidate has no evidence for 'protein'.",
                source=source,
            )
        ],
        guideline_results=[],
        explanation=[],
    )

    authority = fit.nutrition_plan_authority
    assert authority.state == "partial_plan_coverage"
    assert authority.unknown_evidence == ["rule:plan-rule:protein:unknown"]
    assert fit.eligible is False


def test_standalone_rule_does_not_create_plan_authority() -> None:
    standalone = _rule(
        source=_standalone_source(),
        rule_id="constraint:standalone-protein",
    )
    effective = _effective(plans=[], rules=[standalone])

    authority = effective.nutrition_plan_authority
    assert authority.state == "no_active_plan"
    assert authority.plan_rule_ids == []
