from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.daily_nutrition_state import (
    DailyNutritionState,
    DailyNutritionStateComponent,
)
from app.models.family import Family
from app.models.food_catalog import (
    FoodCompositionSnapshot,
    FoodItem,
    FoodItemClassification,
    FoodNutrientComponent,
)
from app.models.nutrition_constraint import NutritionConstraint
from app.models.person import Person
from app.schemas.meal_plan_fit import MealPlanFitCreate
from app.schemas.meal_recommendation import MealRecommendationCandidateInput
from app.schemas.nutrition_plan import (
    NutritionPlanCreate,
    NutritionPlanGuidelineCreate,
    NutritionPlanRuleCreate,
    NutritionPlanUpdate,
)
from app.services.meal_plan_fit import evaluate_meal_plan_fit
from app.services.nutrition_plan import (
    add_nutrition_plan_guideline,
    add_nutrition_plan_rule,
    create_nutrition_plan,
    update_nutrition_plan,
)


def _person(db_session: Session) -> Person:
    family = Family(name="Plan Fit Family", timezone="Europe/Lisbon")
    person = Person(
        family=family,
        first_name="Fit",
        last_name="Tester",
        birth_date=date(1980, 1, 1),
        preferred_locale="pt-PT",
        timezone="Europe/Lisbon",
    )
    db_session.add(person)
    db_session.commit()
    return person


def _dish(db_session: Session, person: Person) -> FoodCompositionSnapshot:
    food = FoodItem(
        family_id=person.family_id,
        catalog_key="fit-test-dish",
        name="Protein lunch",
        food_kind="dish",
        suitable_meal_types=["lunch", "dinner"],
        source="user",
    )
    composition = FoodCompositionSnapshot(
        food_item=food,
        reference_quantity=Decimal(100),
        reference_unit="g",
        energy_kcal=Decimal(220),
        data_version="fit-test-v1",
        source="user",
        effective_at=datetime(2026, 9, 15, 12, 0, tzinfo=UTC),
    )
    composition.nutrients.extend(
        [
            FoodNutrientComponent(
                nutrient_key="protein",
                value=Decimal(30),
                unit="g",
            ),
            FoodNutrientComponent(
                nutrient_key="sodium",
                value=Decimal(400),
                unit="mg",
            ),
        ]
    )
    db_session.add(composition)
    db_session.commit()
    return composition


def _activate_lunch_protein_plan(db_session: Session, person: Person) -> None:
    plan = create_nutrition_plan(
        db_session,
        person=person,
        data=NutritionPlanCreate(
            title="Lunch protein plan",
            source_type="nutritionist",
            source_name="Test Nutritionist",
            status="draft",
            valid_from=date(2026, 9, 1),
        ),
    )
    protein = NutritionConstraint(
        person_id=person.id,
        constraint_type="nutrient_target",
        target_type="nutrient",
        target_key="protein",
        operator="min",
        value_min=Decimal(25),
        unit="g",
        severity="required",
        is_mandatory=True,
        source="nutritionist",
        source_name="Test Nutritionist",
    )
    db_session.add(protein)
    db_session.commit()
    add_nutrition_plan_rule(
        db_session,
        plan=plan,
        data=NutritionPlanRuleCreate(
            rule_kind="constraint",
            reference_id=protein.id,
            meal_type="lunch",
            source_statement="At least 25 g protein at lunch",
        ),
    )
    update_nutrition_plan(
        db_session,
        plan=plan,
        data=NutritionPlanUpdate(status="active"),
    )


def _daily_sodium_limit(db_session: Session, person: Person) -> None:
    db_session.add(
        NutritionConstraint(
            person_id=person.id,
            constraint_type="nutrient_limit",
            target_type="nutrient",
            target_key="sodium",
            operator="max",
            value_max=Decimal(1000),
            unit="mg",
            severity="required",
            is_mandatory=True,
            source="clinician",
            source_name="Test Clinic",
        )
    )
    db_session.commit()


def _daily_state(db_session: Session, person: Person) -> DailyNutritionState:
    state = DailyNutritionState(
        person_id=person.id,
        state_date=date(2026, 9, 15),
        timezone="Europe/Lisbon",
        energy_consumed_kcal=Decimal(500),
        energy_planned_kcal=Decimal(0),
        energy_assumed_kcal=Decimal(0),
        calculation_version="plan-fit-test-v1",
    )
    state.components.append(
        DailyNutritionStateComponent(
            target_type="nutrient",
            target_key="sodium",
            consumed_value=Decimal(700),
            planned_value=Decimal(0),
            unit="mg",
        )
    )
    db_session.add(state)
    db_session.commit()
    return state


def _request(composition: FoodCompositionSnapshot, state_id=None) -> MealPlanFitCreate:
    return MealPlanFitCreate(
        planning_date=date(2026, 9, 15),
        meal_type="lunch",
        daily_nutrition_state_id=state_id,
        candidate=MealRecommendationCandidateInput(
            candidate_kind="food_item",
            composition_id=composition.id,
            quantity=Decimal(100),
            quantity_unit="g",
        ),
    )


def test_plan_fit_food_category_exclusion_uses_only_persisted_classification(
    db_session: Session,
) -> None:
    person = _person(db_session)
    composition = _dish(db_session, person)
    composition.food_item.name = "Gluten flour named food"

    plan = create_nutrition_plan(
        db_session,
        person=person,
        data=NutritionPlanCreate(
            title="Gluten exclusion",
            source_type="nutritionist",
            status="draft",
            valid_from=date(2026, 9, 1),
        ),
    )
    exclusion = NutritionConstraint(
        person_id=person.id,
        constraint_type="exclusion",
        target_type="food_category",
        target_key="gluten",
        operator="exclude",
        severity="required",
        is_mandatory=True,
        source="nutritionist",
    )
    db_session.add(exclusion)
    db_session.flush()
    add_nutrition_plan_rule(
        db_session,
        plan=plan,
        data=NutritionPlanRuleCreate(
            rule_kind="constraint",
            reference_id=exclusion.id,
            meal_type="lunch",
            source_statement="Evitar glúten.",
        ),
    )
    update_nutrition_plan(
        db_session,
        plan=plan,
        data=NutritionPlanUpdate(status="active"),
    )

    without_metadata = evaluate_meal_plan_fit(
        db_session,
        person_id=person.id,
        data=_request(composition),
    )
    unclassified_rule = next(
        rule
        for rule in without_metadata.rule_results
        if rule.target_type == "food_category" and rule.target_key == "gluten"
    )
    assert unclassified_rule.status == "pass"
    assert without_metadata.eligible is True

    composition.food_item.classifications.append(
        FoodItemClassification(
            classification_type="food_category",
            classification_key="gluten",
            source="test",
        )
    )
    db_session.commit()

    with_metadata = evaluate_meal_plan_fit(
        db_session,
        person_id=person.id,
        data=_request(composition),
    )
    classified_rule = next(
        rule
        for rule in with_metadata.rule_results
        if rule.target_type == "food_category" and rule.target_key == "gluten"
    )
    assert classified_rule.status == "fail"
    assert with_metadata.eligible is False


def test_plan_fit_combines_meal_rule_with_daily_mandatory_limit(
    db_session: Session,
) -> None:
    person = _person(db_session)
    composition = _dish(db_session, person)
    _activate_lunch_protein_plan(db_session, person)
    _daily_sodium_limit(db_session, person)
    state = _daily_state(db_session, person)

    result = evaluate_meal_plan_fit(
        db_session,
        person_id=person.id,
        data=_request(composition, state.id),
    )

    assert result.status == "fail"
    assert result.eligible is False
    assert result.fit_score == Decimal("1.0000")

    protein = next(rule for rule in result.rule_results if rule.target_key == "protein")
    assert protein.scope == "meal"
    assert protein.status == "pass"
    assert protein.observed_value == Decimal("30.0000")

    sodium = next(rule for rule in result.rule_results if rule.target_key == "sodium")
    assert sodium.scope == "daily"
    assert sodium.status == "fail"
    assert sodium.observed_value == Decimal("400.0000")
    assert sodium.projected_daily_value == Decimal("1100.0000")


def test_plan_fit_keeps_unsupported_mandatory_rule_visible_without_universal_veto(
    db_session: Session,
) -> None:
    person = _person(db_session)
    composition = _dish(db_session, person)
    plan = create_nutrition_plan(
        db_session,
        person=person,
        data=NutritionPlanCreate(
            title="Lifestyle plan",
            source_type="nutritionist",
            status="draft",
            valid_from=date(2026, 9, 1),
        ),
    )
    activity = NutritionConstraint(
        person_id=person.id,
        constraint_type="activity_target",
        target_type="activity",
        target_key="daily_steps",
        operator="min",
        value_min=Decimal(8000),
        unit="steps/day",
        severity="required",
        is_mandatory=True,
        source="nutritionist",
    )
    db_session.add(activity)
    db_session.commit()
    add_nutrition_plan_rule(
        db_session,
        plan=plan,
        data=NutritionPlanRuleCreate(
            rule_kind="constraint",
            reference_id=activity.id,
            source_statement="Pelo menos 8000 passos por dia.",
        ),
    )
    update_nutrition_plan(
        db_session,
        plan=plan,
        data=NutritionPlanUpdate(status="active"),
    )

    result = evaluate_meal_plan_fit(
        db_session,
        person_id=person.id,
        data=_request(composition),
    )

    assert result.eligible is True
    rule = next(item for item in result.rule_results if item.target_key == "daily_steps")
    assert rule.status == "not_evaluated"
    assert result.nutrition_plan_authority.state == "partial_plan_coverage"
    assert any("does not by itself veto" in text for text in result.explanation)


def test_plan_fit_does_not_guess_food_category_exclusion_without_structured_evidence(
    db_session: Session,
) -> None:
    person = _person(db_session)
    composition = _dish(db_session, person)
    plan = create_nutrition_plan(
        db_session,
        person=person,
        data=NutritionPlanCreate(
            title="Soy exclusion plan",
            source_type="nutritionist",
            status="draft",
            valid_from=date(2026, 9, 1),
        ),
    )
    exclusion = NutritionConstraint(
        person_id=person.id,
        constraint_type="exclusion",
        target_type="food_category",
        target_key="soy",
        operator="exclude",
        severity="required",
        is_mandatory=True,
        source="nutritionist",
    )
    db_session.add(exclusion)
    db_session.commit()
    add_nutrition_plan_rule(
        db_session,
        plan=plan,
        data=NutritionPlanRuleCreate(
            rule_kind="constraint",
            reference_id=exclusion.id,
            source_statement="Evitar soja.",
        ),
    )
    update_nutrition_plan(
        db_session,
        plan=plan,
        data=NutritionPlanUpdate(status="active"),
    )

    result = evaluate_meal_plan_fit(
        db_session,
        person_id=person.id,
        data=_request(composition),
    )

    rule = next(item for item in result.rule_results if item.target_key == "soy")
    assert rule.status == "not_evaluated"
    assert result.eligible is True
    assert result.status == "unknown"
    assert result.nutrition_plan_authority.state == "partial_plan_coverage"
    assert "cannot yet evaluate target type 'food_category'" in rule.explanation


def test_plan_fit_keeps_mandatory_qualitative_guideline_visible_without_universal_veto(
    db_session: Session,
) -> None:
    person = _person(db_session)
    composition = _dish(db_session, person)
    plan = create_nutrition_plan(
        db_session,
        person=person,
        data=NutritionPlanCreate(
            title="Qualitative plan",
            source_type="nutritionist",
            status="draft",
            valid_from=date(2026, 9, 1),
        ),
    )
    add_nutrition_plan_guideline(
        db_session,
        plan=plan,
        data=NutritionPlanGuidelineCreate(
            guideline_type="qualitative",
            target_type="food_category",
            target_key="cereals",
            description="Evitar cereais refinados.",
            is_mandatory=True,
            priority=120,
        ),
    )
    update_nutrition_plan(
        db_session,
        plan=plan,
        data=NutritionPlanUpdate(status="active"),
    )

    result = evaluate_meal_plan_fit(
        db_session,
        person_id=person.id,
        data=_request(composition),
    )

    assert result.eligible is True
    assert len(result.guideline_results) == 1
    assert result.guideline_results[0].status == "not_evaluated"
    assert result.nutrition_plan_authority.state == "partial_plan_coverage"


def test_plan_fit_fails_closed_when_mandatory_daily_context_is_missing(
    db_session: Session,
) -> None:
    person = _person(db_session)
    composition = _dish(db_session, person)
    _activate_lunch_protein_plan(db_session, person)
    _daily_sodium_limit(db_session, person)

    result = evaluate_meal_plan_fit(
        db_session,
        person_id=person.id,
        data=_request(composition),
    )

    assert result.status == "unknown"
    assert result.eligible is False
    sodium = next(rule for rule in result.rule_results if rule.target_key == "sodium")
    assert sodium.status == "unknown"
    assert "Daily rule requires DailyNutritionState" in sodium.explanation
