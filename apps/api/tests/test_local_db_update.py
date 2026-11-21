from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.development_breakfast_seed import seed_development_breakfast_catalog
from app.local_db_update import apply_catalogue_updates
from app.models.family import Family
from app.models.food_catalog import FoodItem, Recipe
from app.models.meal_candidate_planning_profile import MealCandidatePlanningProfile
from app.models.food_transformation_profile import FoodTransformationProfile


def test_local_catalogue_update_never_creates_a_family_or_breakfast(
    db_session: Session,
) -> None:
    assert apply_catalogue_updates(db_session) == (0, 0)
    assert db_session.scalar(select(func.count()).select_from(Family)) == 0
    assert db_session.scalar(select(func.count()).select_from(FoodItem)) == 0


def test_local_catalogue_update_adds_only_missing_reference_data_and_is_idempotent(
    db_session: Session,
) -> None:
    family = Family(name="Família preservada", timezone="Europe/Lisbon")
    db_session.add(family)
    db_session.flush()
    seed_development_breakfast_catalog(db_session, families=(family,))
    before_recipes = db_session.scalar(
        select(func.count()).select_from(FoodItem).where(FoodItem.food_kind == "dish")
    )

    first = apply_catalogue_updates(db_session)
    count_after_first = db_session.scalar(
        select(func.count()).select_from(FoodTransformationProfile)
    )
    second = apply_catalogue_updates(db_session)
    count_after_second = db_session.scalar(
        select(func.count()).select_from(FoodTransformationProfile)
    )

    assert first == second == (5, 2)
    assert count_after_first == count_after_second == 5
    assert db_session.scalar(select(func.count()).select_from(Family)) == 1
    assert db_session.get(Family, family.id).name == "Família preservada"
    assert db_session.scalar(
        select(func.count()).select_from(FoodItem).where(FoodItem.food_kind == "dish")
    ) == before_recipes


def test_local_catalogue_update_bootstraps_breakfast_for_existing_family(
    db_session: Session,
) -> None:
    family = Family(name="Família sem catálogo", timezone="Europe/Lisbon")
    db_session.add(family)
    db_session.flush()
    first = apply_catalogue_updates(db_session)
    assert first == (5, 2)
    assert db_session.scalar(
        select(func.count()).select_from(Recipe).where(
            Recipe.source == "development-breakfast"
        )
    ) == 11
    assert db_session.scalar(
        select(func.count()).select_from(MealCandidatePlanningProfile).where(
            MealCandidatePlanningProfile.family_id == family.id,
            MealCandidatePlanningProfile.source == "development-breakfast",
        )
    ) == 11
    assert db_session.scalar(select(func.count()).select_from(FoodTransformationProfile)) == 5
    assert apply_catalogue_updates(db_session) == (5, 2)
    assert db_session.scalar(
        select(func.count()).select_from(Recipe).where(
            Recipe.source == "development-breakfast"
        )
    ) == 11
    assert db_session.scalar(select(func.count()).select_from(Family)) == 1
