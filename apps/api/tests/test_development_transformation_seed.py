from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.demo_seed import seed_demo_dataset
from app.development_breakfast_seed import seed_development_breakfast_catalog
from app.development_transformation_seed import (
    DEFINITIONS,
    TRANSFORMATION_DATA_VERSION,
    seed_development_transformations,
)
from app.models.family import Family
from app.models.food_catalog import FoodCompositionSnapshot
from app.models.food_transformation_profile import FoodTransformationProfile


def test_development_transformation_seed_is_idempotent(db_session: Session) -> None:
    demo = seed_demo_dataset(db_session)
    family = db_session.get(Family, demo.family_id)
    assert family is not None
    seed_development_breakfast_catalog(db_session, families=(family,))

    first = seed_development_transformations(db_session, families=(family,))
    second = seed_development_transformations(db_session, families=(family,))
    db_session.commit()

    assert first.profile_count == len(DEFINITIONS)
    assert second.profile_count == len(DEFINITIONS)

    profile_count = db_session.scalar(
        select(func.count())
        .select_from(FoodTransformationProfile)
        .where(FoodTransformationProfile.family_id == family.id)
    )
    composition_count = db_session.scalar(
        select(func.count())
        .select_from(FoodCompositionSnapshot)
        .where(FoodCompositionSnapshot.data_version == TRANSFORMATION_DATA_VERSION)
    )

    assert profile_count == len(DEFINITIONS)
    assert composition_count == len(DEFINITIONS)
