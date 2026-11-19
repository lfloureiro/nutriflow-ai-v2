from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.models.family import Family
from app.models.person import Person
from app.schemas.nutrition_plan import NutritionPlanUpdate
from app.schemas.nutrition_plan_import import (
    NutritionPlanImportCreate,
    NutritionPlanImportProposalUpdate,
)
from app.services.nutrition_plan import (
    compile_effective_nutrition_plan,
    update_nutrition_plan,
)
from app.services.nutrition_plan_import import (
    NutritionPlanImportError,
    apply_nutrition_plan_import,
    create_nutrition_plan_import,
    update_nutrition_plan_import_proposal,
)


def _person(db_session: Session) -> Person:
    family = Family(name="Import Test Family", timezone="Europe/Lisbon")
    person = Person(
        family=family,
        first_name="Import",
        last_name="Tester",
        birth_date=date(1985, 6, 10),
        preferred_locale="pt-PT",
        timezone="Europe/Lisbon",
    )
    db_session.add(person)
    db_session.commit()
    return person


def test_import_requires_explicit_review_before_materialization(db_session: Session) -> None:
    person = _person(db_session)
    import_session = create_nutrition_plan_import(
        db_session,
        person=person,
        data=NutritionPlanImportCreate(
            title="Plano da nutricionista",
            source_type="nutritionist",
            source_name="Dra. Teste",
            source_reference="consultation-2026-09-15",
            source_text=(
                "Protein 45-55 g at lunch\n"
                "Sodium <= 2000 mg/day\n"
                "Fish >= 3 meals/week\n"
                "Prefer salad and vegetables at lunch\n"
                "Handwritten note with unclear meaning"
            ),
            valid_from=date(2026, 9, 15),
        ),
    )

    assert import_session.status == "review"
    assert import_session.nutrition_plan.status == "draft"
    assert import_session.nutrition_plan.original_text == import_session.source_text
    assert len(import_session.proposals) == 5

    proposals = {proposal.ordinal: proposal for proposal in import_session.proposals}
    assert proposals[1].proposal_type == "numeric_rule"
    assert proposals[1].target_key == "protein"
    assert proposals[1].operator == "range"
    assert proposals[1].value_min == Decimal(45)
    assert proposals[1].value_max == Decimal(55)
    assert proposals[1].meal_type == "lunch"

    assert proposals[2].proposal_type == "numeric_rule"
    assert proposals[2].target_key == "sodium"
    assert proposals[2].operator == "max"
    assert proposals[2].value_max == Decimal(2000)

    assert proposals[3].proposal_type == "frequency_guideline"
    assert proposals[3].target_key == "fish"
    assert proposals[3].minimum_occurrences == 3
    assert proposals[3].period == "week"

    assert proposals[4].proposal_type == "qualitative_guideline"
    assert proposals[4].meal_type == "lunch"
    assert proposals[5].proposal_type == "unclassified"

    with pytest.raises(
        NutritionPlanImportError,
        match="explicitly confirmed or rejected",
    ):
        apply_nutrition_plan_import(db_session, import_session=import_session)

    for ordinal, confirmation in {
        1: "confirmed",
        2: "rejected",
        3: "confirmed",
        4: "confirmed",
        5: "rejected",
    }.items():
        update_nutrition_plan_import_proposal(
            db_session,
            import_session=import_session,
            proposal_id=proposals[ordinal].id,
            data=NutritionPlanImportProposalUpdate(
                confirmation_status=confirmation,
            ),
        )

    applied = apply_nutrition_plan_import(db_session, import_session=import_session)
    assert applied.status == "applied"
    assert applied.nutrition_plan.status == "draft"

    applied_proposals = {proposal.ordinal: proposal for proposal in applied.proposals}
    assert applied_proposals[1].nutrition_plan_rule_id is not None
    assert applied_proposals[2].nutrition_plan_rule_id is None
    assert applied_proposals[3].nutrition_plan_guideline_id is not None
    assert applied_proposals[4].nutrition_plan_guideline_id is not None
    assert applied_proposals[5].nutrition_plan_guideline_id is None

    plan = applied.nutrition_plan
    assert len(plan.rules) == 1
    assert len(plan.guidelines) == 2
    protein_constraint = plan.rules[0].nutrition_constraint
    assert protein_constraint is not None
    assert protein_constraint.source == "nutritionist"
    assert protein_constraint.source_name == "Dra. Teste"
    assert protein_constraint.target_key == "protein"
    assert plan.rules[0].source_statement == "Protein 45-55 g at lunch"

    activated = update_nutrition_plan(
        db_session,
        plan=plan,
        data=NutritionPlanUpdate(status="active"),
    )
    assert activated.status == "active"

    effective = compile_effective_nutrition_plan(
        db_session,
        person_id=person.id,
        on_date=date(2026, 9, 15),
        meal_type="lunch",
    )
    protein_rules = [rule for rule in effective.numeric_rules if rule.target_key == "protein"]
    assert len(protein_rules) == 1
    assert protein_rules[0].value_min == Decimal(45)
    assert protein_rules[0].value_max == Decimal(55)
    assert any(
        guideline.guideline_type == "frequency" and guideline.target_key == "fish"
        for guideline in effective.guidelines
    )

    with pytest.raises(NutritionPlanImportError, match="Only imports in review"):
        update_nutrition_plan_import_proposal(
            db_session,
            import_session=applied,
            proposal_id=applied_proposals[1].id,
            data=NutritionPlanImportProposalUpdate(review_notes="Too late"),
        )


def test_explicit_food_category_exclusion_materializes_as_plan_constraint(
    db_session: Session,
) -> None:
    person = _person(db_session)
    import_session = create_nutrition_plan_import(
        db_session,
        person=person,
        data=NutritionPlanImportCreate(
            title="Plano com exclusão",
            source_type="nutritionist",
            source_name="Dra. Teste",
            source_text="Evitar soja",
            valid_from=date(2026, 9, 15),
        ),
    )

    proposal = import_session.proposals[0]
    assert proposal.proposal_type == "numeric_rule"
    assert proposal.target_type == "food_category"
    assert proposal.target_key == "soy"
    assert proposal.operator == "exclude"
    assert proposal.value_min is None
    assert proposal.value_max is None
    assert proposal.value_target is None
    assert proposal.unit is None
    assert proposal.is_mandatory is True

    update_nutrition_plan_import_proposal(
        db_session,
        import_session=import_session,
        proposal_id=proposal.id,
        data=NutritionPlanImportProposalUpdate(confirmation_status="confirmed"),
    )
    applied = apply_nutrition_plan_import(
        db_session,
        import_session=import_session,
    )

    assert applied.nutrition_plan.status == "draft"
    assert len(applied.nutrition_plan.rules) == 1
    constraint = applied.nutrition_plan.rules[0].nutrition_constraint
    assert constraint is not None
    assert constraint.constraint_type == "exclusion"
    assert constraint.target_type == "food_category"
    assert constraint.target_key == "soy"
    assert constraint.operator == "exclude"
    assert constraint.is_mandatory is True


def test_confirmed_unclassified_proposal_cannot_be_applied(db_session: Session) -> None:
    person = _person(db_session)
    import_session = create_nutrition_plan_import(
        db_session,
        person=person,
        data=NutritionPlanImportCreate(
            title="Ambiguous plan",
            source_type="user",
            source_text="Something unclear and not safely parseable",
            valid_from=date(2026, 9, 15),
        ),
    )
    proposal = import_session.proposals[0]
    assert proposal.proposal_type == "unclassified"

    update_nutrition_plan_import_proposal(
        db_session,
        import_session=import_session,
        proposal_id=proposal.id,
        data=NutritionPlanImportProposalUpdate(confirmation_status="confirmed"),
    )

    with pytest.raises(NutritionPlanImportError, match="still unclassified"):
        apply_nutrition_plan_import(db_session, import_session=import_session)
