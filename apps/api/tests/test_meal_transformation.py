from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.demo_seed import DEMO_PERSON_ID, seed_demo_dataset
from app.development_breakfast_seed import seed_development_breakfast_catalog
from app.development_plan_fit_seed import seed_development_plan_fit
from app.development_transformation_seed import seed_development_transformations
from app.models.family import Family
from app.models.food_catalog import Recipe
from app.schemas.meal_transformation import MealTransformationCreate
from app.services.meal_transformation import propose_meal_transformations


def _seed(db_session: Session):
    demo = seed_demo_dataset(
        db_session,
        now=datetime(2026, 9, 15, 12, 0, tzinfo=UTC),
    )
    family = db_session.get(Family, demo.family_id)
    assert family is not None
    seed_development_breakfast_catalog(db_session, families=(family,))
    seed_development_transformations(db_session, families=(family,))
    seed_development_plan_fit(db_session, person_id=DEMO_PERSON_ID)
    db_session.commit()
    return demo


def test_yogurt_replacement_resolves_mandatory_breakfast_protein(db_session: Session) -> None:
    demo = _seed(db_session)
    recipe = db_session.query(Recipe).filter_by(
        recipe_key="breakfast:recipe:yogurt-muesli-banana"
    ).one()

    result = propose_meal_transformations(
        db_session,
        person_id=DEMO_PERSON_ID,
        data=MealTransformationCreate(
            planning_date=demo.planning_date,
            meal_type="breakfast",
            recipe_id=recipe.id,
            quantity=Decimal(1),
            quantity_unit="serving",
            daily_nutrition_state_id=demo.daily_nutrition_state_id,
        ),
    )

    assert result.baseline_fit.eligible is False
    assert result.baseline_fit.fit_score == Decimal("0.9667")
    assert result.proposals

    proposal = next(
        item
        for item in result.proposals
        if item.operation.replacement_food_name == "Iogurte grego"
    )
    assert proposal.operation.source_food_name == "Iogurte natural"
    assert proposal.operation.source_quantity == Decimal(170)
    assert proposal.operation.replacement_quantity == Decimal(170)
    assert proposal.operation.replacement_unit == "g"
    assert proposal.resolves_mandatory_block is True
    assert proposal.after_fit.eligible is True
    assert proposal.after_fit.fit_score == Decimal("1.0000")
    assert proposal.fit_score_delta == Decimal("0.0333")
    assert "mandatory_block_resolved" in proposal.explanation


def test_transformation_engine_does_not_offer_worse_replacement(db_session: Session) -> None:
    demo = _seed(db_session)
    recipe = db_session.query(Recipe).filter_by(
        recipe_key="breakfast:recipe:greek-yogurt-muesli-berries"
    ).one()

    result = propose_meal_transformations(
        db_session,
        person_id=DEMO_PERSON_ID,
        data=MealTransformationCreate(
            planning_date=demo.planning_date,
            meal_type="breakfast",
            recipe_id=recipe.id,
            quantity=Decimal(1),
            quantity_unit="serving",
            daily_nutrition_state_id=demo.daily_nutrition_state_id,
        ),
    )

    assert result.baseline_fit.eligible is True
    assert result.baseline_fit.fit_score == Decimal("1.0000")
    assert result.proposals == []
