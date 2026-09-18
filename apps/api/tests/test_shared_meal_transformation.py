from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.demo_seed import (
    DEMO_FAMILY_ID,
    DEMO_MARTA_ID,
    DEMO_PERSON_ID,
    DEMO_RUI_ID,
    seed_demo_dataset,
)
from app.development_breakfast_seed import seed_development_breakfast_catalog
from app.development_plan_fit_seed import PROTEIN_RULE_ID, seed_development_plan_fit
from app.development_transformation_seed import seed_development_transformations
from app.models.daily_nutrition_state import DailyNutritionState
from app.models.family import Family
from app.models.food_adverse_reaction import FoodAdverseReaction
from app.models.food_catalog import Recipe
from app.models.food_preference import FoodPreference
from app.models.meal import MealEvent, Serving
from app.models.meal_transformation_application import MealTransformationApplication
from app.schemas.shared_meal_transformation import (
    SharedMealTransformationCreate,
    SharedMealTransformationParticipantCreate,
    SharedMealTransformationPlanCreate,
)
from app.services.shared_meal_transformation import (
    plan_shared_meal_transformation,
    propose_shared_meal_transformations,
)


def _seed(db_session: Session):
    demo = seed_demo_dataset(
        db_session,
        now=datetime(2026, 9, 15, 12, 0, tzinfo=UTC),
    )
    family = db_session.get(Family, demo.family_id)
    assert family is not None
    seed_development_breakfast_catalog(db_session, families=(family,))
    seed_development_transformations(db_session, families=(family,))
    db_session.commit()
    recipe = db_session.scalar(
        select(Recipe).where(
            Recipe.recipe_key == "breakfast:recipe:yogurt-muesli-banana"
        )
    )
    assert recipe is not None
    return demo, recipe


def _state(db_session: Session, person_id, planning_date) -> DailyNutritionState:
    state = db_session.scalar(
        select(DailyNutritionState).where(
            DailyNutritionState.person_id == person_id,
            DailyNutritionState.state_date == planning_date,
        )
    )
    assert state is not None
    return state


def _participant(person_id, state: DailyNutritionState):
    assert state.id is not None
    return SharedMealTransformationParticipantCreate(
        person_id=person_id,
        daily_nutrition_state_id=state.id,
        quantity=Decimal(1),
        quantity_unit="serving",
    )


def test_shared_transformation_is_plan_adapted_when_one_plan_improves_and_all_are_safe(
    db_session: Session,
) -> None:
    demo, recipe = _seed(db_session)
    seed_development_plan_fit(db_session, person_id=DEMO_PERSON_ID)
    db_session.commit()
    person_state = _state(db_session, DEMO_PERSON_ID, demo.planning_date)
    marta_state = _state(db_session, DEMO_MARTA_ID, demo.planning_date)

    result = propose_shared_meal_transformations(
        db_session,
        family_id=DEMO_FAMILY_ID,
        data=SharedMealTransformationCreate(
            planning_date=demo.planning_date,
            meal_type="breakfast",
            recipe_id=recipe.id,
            participants=[
                _participant(DEMO_PERSON_ID, person_state),
                _participant(DEMO_MARTA_ID, marta_state),
            ],
        ),
    )

    proposal = next(
        item
        for item in result.proposals
        if item.operation.replacement_food_name == "Iogurte grego"
    )
    assert proposal.kind == "plan_adapted"
    assert proposal.plan_improvement_participants == 1
    assert "plan_backed_family_improvement" in proposal.explanation

    by_person = {item.person_id: item for item in proposal.participant_results}
    primary = by_person[DEMO_PERSON_ID]
    assert f"plan-rule:{PROTEIN_RULE_ID}" in primary.plan_improved_rule_ids
    assert primary.before_fit.eligible is False
    assert primary.after_fit.eligible is True
    assert primary.after_fit.nutrition_plan_authority.state == "partial_plan_coverage"

    marta = by_person[DEMO_MARTA_ID]
    assert marta.after_fit.eligible is True
    assert marta.plan_improved_rule_ids == []
    assert marta.after_fit.nutrition_plan_authority.state == "no_active_plan"


def test_no_plan_transformation_is_labelled_only_as_preference_variant(
    db_session: Session,
) -> None:
    demo, recipe = _seed(db_session)
    for person_id in (DEMO_MARTA_ID, DEMO_RUI_ID):
        db_session.add(
            FoodPreference(
                person_id=person_id,
                subject_type="ingredient",
                subject_key="breakfast:ingredient:greek-yogurt",
                preference_type="like",
                intensity=5,
                source="user",
            )
        )
    db_session.commit()
    marta_state = _state(db_session, DEMO_MARTA_ID, demo.planning_date)
    rui_state = _state(db_session, DEMO_RUI_ID, demo.planning_date)

    result = propose_shared_meal_transformations(
        db_session,
        family_id=DEMO_FAMILY_ID,
        data=SharedMealTransformationCreate(
            planning_date=demo.planning_date,
            meal_type="breakfast",
            recipe_id=recipe.id,
            participants=[
                _participant(DEMO_MARTA_ID, marta_state),
                _participant(DEMO_RUI_ID, rui_state),
            ],
        ),
    )

    proposal = next(
        item
        for item in result.proposals
        if item.operation.replacement_food_name == "Iogurte grego"
    )
    assert proposal.kind == "preference_variant"
    assert proposal.plan_improvement_participants == 0
    assert proposal.preference_improvement_participants == 2
    assert proposal.minimum_preference_delta > 0
    assert "family_preference_improved_without_plan_claim" in proposal.explanation
    assert all(
        item.after_fit.nutrition_plan_authority.state == "no_active_plan"
        for item in proposal.participant_results
    )


def test_shared_transformation_is_rejected_when_replacement_is_unsafe_for_one_person(
    db_session: Session,
) -> None:
    demo, recipe = _seed(db_session)
    seed_development_plan_fit(db_session, person_id=DEMO_PERSON_ID)
    db_session.add(
        FoodAdverseReaction(
            person_id=DEMO_MARTA_ID,
            reaction_type="intolerance",
            subject_type="ingredient",
            subject_key="breakfast:ingredient:greek-yogurt",
            severity="high",
            is_mandatory=True,
            source="user",
            start_date=demo.planning_date,
        )
    )
    db_session.commit()
    person_state = _state(db_session, DEMO_PERSON_ID, demo.planning_date)
    marta_state = _state(db_session, DEMO_MARTA_ID, demo.planning_date)

    result = propose_shared_meal_transformations(
        db_session,
        family_id=DEMO_FAMILY_ID,
        data=SharedMealTransformationCreate(
            planning_date=demo.planning_date,
            meal_type="breakfast",
            recipe_id=recipe.id,
            participants=[
                _participant(DEMO_PERSON_ID, person_state),
                _participant(DEMO_MARTA_ID, marta_state),
            ],
        ),
    )

    assert not any(
        item.operation.replacement_food_name == "Iogurte grego"
        for item in result.proposals
    )



def _cancel_seed_breakfast(db_session: Session, planning_date) -> None:
    event = db_session.scalar(
        select(MealEvent).where(
            MealEvent.family_id == DEMO_FAMILY_ID,
            MealEvent.meal_type == "breakfast",
        )
    )
    assert event is not None
    event.status = "cancelled"
    db_session.flush()


def test_plan_shared_transformation_persists_operation_and_transformed_nutrition(
    db_session: Session,
) -> None:
    demo, recipe = _seed(db_session)
    seed_development_plan_fit(db_session, person_id=DEMO_PERSON_ID)
    db_session.commit()
    _cancel_seed_breakfast(db_session, demo.planning_date)

    person_state = _state(db_session, DEMO_PERSON_ID, demo.planning_date)
    marta_state = _state(db_session, DEMO_MARTA_ID, demo.planning_date)
    participants = [
        _participant(DEMO_PERSON_ID, person_state),
        _participant(DEMO_MARTA_ID, marta_state),
    ]
    preview = propose_shared_meal_transformations(
        db_session,
        family_id=DEMO_FAMILY_ID,
        data=SharedMealTransformationCreate(
            planning_date=demo.planning_date,
            meal_type="breakfast",
            recipe_id=recipe.id,
            participants=participants,
        ),
    )
    proposal = next(
        item
        for item in preview.proposals
        if item.operation.replacement_food_name == "Iogurte grego"
    )
    expected_energy = {
        item.person_id: item.after_fit.candidate.nutrition.energy_kcal
        for item in proposal.participant_results
    }

    planned = plan_shared_meal_transformation(
        db_session,
        family_id=DEMO_FAMILY_ID,
        data=SharedMealTransformationPlanCreate(
            planning_date=demo.planning_date,
            meal_type="breakfast",
            recipe_id=recipe.id,
            participants=participants,
            recipe_ingredient_id=proposal.operation.recipe_ingredient_id,
            replacement_food_item_id=proposal.operation.replacement_food_item_id,
            scheduled_at=datetime(2026, 9, 15, 8, 30, tzinfo=UTC),
            title="Pequeno-almoço adaptado",
        ),
    )

    assert planned.transformation_kind == "plan_adapted"
    application = db_session.get(
        MealTransformationApplication,
        planned.transformation_application_id,
    )
    assert application is not None
    assert application.meal_event_id == planned.meal_event_id
    assert application.recipe_id == recipe.id
    assert application.source_recipe_composition_snapshot_id is not None
    assert application.replacement_food_item_id == proposal.operation.replacement_food_item_id
    assert application.evidence["classification"] == "plan_adapted"

    servings = list(
        db_session.scalars(
            select(Serving)
            .join(Serving.meal_participant)
            .where(Serving.meal_participant.has(meal_event_id=planned.meal_event_id))
        ).all()
    )
    assert len(servings) == 2
    for serving in servings:
        person_id = serving.meal_participant.person_id
        assert serving.recipe_id == recipe.id
        assert serving.recipe_composition_snapshot_id is None
        assert serving.nutrition_source == "transformed"
        assert serving.source_reference == f"meal-transformation:{application.id}"
        assert serving.energy_planned_kcal == expected_energy[person_id]
        assert serving.nutrition_components
