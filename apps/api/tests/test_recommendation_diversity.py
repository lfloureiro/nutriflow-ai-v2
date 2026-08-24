import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.food_catalog import Recipe
from app.schemas.practical_recommendation import RecommendationHistoryHint
from app.services.meal_recommendation import (
    CandidateEvaluation,
    MealCandidate,
    RecommendationResult,
)
from app.services.recommendation_diversity import apply_diversity_to_recommendation
from app.services.serving_nutrition import NutritionSnapshot

FAMILY_ID = uuid.UUID("e14db6e5-d284-4b2d-ad43-8dd45b5ec565")
PLANNING_DATE = date(2026, 8, 23)


def _candidate(
    key: str,
    name: str,
    *,
    suitable_meal_types: list[str] | None = None,
) -> MealCandidate:
    recipe = Recipe(
        id=uuid.uuid4(),
        recipe_key=key,
        name=name,
        suitable_meal_types=suitable_meal_types,
        source="test",
        is_active=True,
    )
    return MealCandidate(
        key=key,
        name=name,
        kind="recipe",
        quantity=Decimal(1),
        quantity_unit="serving",
        nutrition=NutritionSnapshot(energy_kcal=Decimal(600), nutrients={}),
        subjects=frozenset({("recipe", key)}),
        recipe=recipe,
    )


def _evaluation(candidate: MealCandidate) -> CandidateEvaluation:
    return CandidateEvaluation(
        candidate=candidate,
        eligible=True,
        rank=None,
        score=Decimal(1),
        score_breakdown={"energy": Decimal(1)},
        exclusion_reasons=(),
        explanation=(),
    )


def test_provisional_previous_day_selection_pushes_repeated_recipe_below_novel_option(
    db_session: Session,
) -> None:
    chicken = _candidate("recipe:chicken", "Frango com arroz")
    salmon = _candidate("recipe:salmon", "Salmão com batata")
    base = RecommendationResult(
        engine_version="test-v1",
        evaluations=(_evaluation(chicken), _evaluation(salmon)),
    )

    result = apply_diversity_to_recommendation(
        db_session,
        family_id=FAMILY_ID,
        planning_date=PLANNING_DATE,
        meal_type="lunch",
        recommendation=base,
        provisional_history=[
            RecommendationHistoryHint(
                plan_date=date(2026, 8, 22),
                candidate_key=chicken.key,
            )
        ],
    )

    assert result.engine_version == "test-v1+diversity-v1"
    assert result.eligible[0].candidate.key == salmon.key
    chicken_result = next(item for item in result.evaluations if item.candidate.key == chicken.key)
    assert chicken_result.score_breakdown["diversity"] <= Decimal("-3.0000")
    assert "variety: used in the last 3 days" in chicken_result.explanation


def test_catalogue_meal_suitability_excludes_breakfast_recipe_from_lunch(
    db_session: Session,
) -> None:
    breakfast = _candidate(
        "recipe:yogurt",
        "Iogurte com muesli",
        suitable_meal_types=["breakfast"],
    )
    lunch = _candidate(
        "recipe:fish",
        "Peixe com arroz",
        suitable_meal_types=["lunch", "dinner"],
    )
    base = RecommendationResult(
        engine_version="test-v1",
        evaluations=(_evaluation(breakfast), _evaluation(lunch)),
    )

    result = apply_diversity_to_recommendation(
        db_session,
        family_id=FAMILY_ID,
        planning_date=PLANNING_DATE,
        meal_type="lunch",
        recommendation=base,
        provisional_history=[],
    )

    breakfast_result = next(
        item for item in result.evaluations if item.candidate.key == breakfast.key
    )
    assert breakfast_result.eligible is False
    assert breakfast_result.exclusion_reasons == (
        "planning_profile:not_suitable_for:lunch",
    )
    assert result.eligible[0].candidate.key == lunch.key
