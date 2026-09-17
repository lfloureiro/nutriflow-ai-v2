import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from app.schemas.meal_plan_fit import (
    MealPlanFitCandidateRead,
    MealPlanFitRead,
    MealPlanFitRuleRead,
)
from app.schemas.meal_recommendation import (
    MealRecommendationOptionRead,
    RecommendationNutritionRead,
)
from app.schemas.nutrition_plan import EffectiveNutritionPlanSourceRead, NutritionPlanRead


def test_recommendation_option_can_carry_server_authoritative_plan_state() -> None:
    now = datetime(2026, 9, 17, 12, 0, tzinfo=UTC)
    person_id = uuid.uuid4()
    plan = NutritionPlanRead(
        id=uuid.uuid4(),
        person_id=person_id,
        lineage_id=uuid.uuid4(),
        version=1,
        supersedes_plan_id=None,
        title="Plan",
        source_type="nutritionist",
        source_name="Nutritionist",
        source_reference="document:test",
        original_text=None,
        status="active",
        valid_from=date(2026, 9, 1),
        valid_until=None,
        created_at=now,
        updated_at=now,
    )
    source = EffectiveNutritionPlanSourceRead(
        plan_id=plan.id,
        plan_title=plan.title,
        plan_source_type=plan.source_type,
        source_name=plan.source_name,
        source_reference=plan.source_reference,
        rule_source="nutritionist",
    )
    nutrition = RecommendationNutritionRead(energy_kcal=Decimal(300), nutrients={})
    fit = MealPlanFitRead(
        person_id=person_id,
        planning_date=date(2026, 9, 17),
        meal_type="dinner",
        daily_nutrition_state_id=None,
        candidate=MealPlanFitCandidateRead(
            key="recipe:test",
            name="Test recipe",
            kind="recipe",
            quantity=Decimal(1),
            quantity_unit="serving",
            nutrition=nutrition,
        ),
        eligible=True,
        status="pass",
        fit_score=Decimal(1),
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
                status="pass",
                is_mandatory=True,
                priority=100,
                observed_value=Decimal(30),
                observed_unit="g",
                target_min=Decimal(25),
                target_unit="g",
                score=Decimal(1),
                explanation="Target met.",
                source=source,
            )
        ],
        guideline_results=[],
        explanation=[],
    )
    option = MealRecommendationOptionRead(
        id=uuid.uuid4(),
        candidate_key="recipe:test",
        candidate_name="Test recipe",
        candidate_kind="recipe",
        quantity=Decimal(1),
        quantity_unit="serving",
        eligible=True,
        rank=1,
        score=Decimal(1),
        score_breakdown={"plan_fit": Decimal(1)},
        exclusion_reasons=[],
        explanation=[],
        nutrition=nutrition,
        nutrition_plan_authority=fit.nutrition_plan_authority,
    )

    dumped = option.model_dump(mode="json")
    assert dumped["nutrition_plan_authority"]["state"] == "active_plan"
    assert dumped["nutrition_plan_authority"]["active_plans"][0]["title"] == "Plan"
