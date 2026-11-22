from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.development_breakfast_seed import seed_development_breakfast_catalog
from app.development_bread_review_seed import (
    CANDIDATES,
    GROUP,
    SOURCE,
    SOURCE_BREAD_KEY,
    seed_development_bread_candidates,
)
from app.models.family import Family
from app.models.food_catalog import FoodCompositionSnapshot, FoodItem, Recipe
from app.models.food_transformation_profile import FoodTransformationProfile
from app.services.shared_meal_transformation import _load_variants


def test_retail_bread_candidates_are_idempotent_and_never_automatically_safe(
    db_session: Session,
) -> None:
    family = Family(name="Família pão em revisão", timezone="Europe/Lisbon")
    db_session.add(family)
    db_session.flush()
    seed_development_breakfast_catalog(db_session, families=(family,))
    assert seed_development_bread_candidates(db_session, families=(family,)) == 3
    assert seed_development_bread_candidates(db_session, families=(family,)) == 3

    products = list(db_session.scalars(
        select(FoodItem).where(FoodItem.source == SOURCE)
    ).all())
    assert {product.catalog_key for product in products} == {
        candidate.key for candidate in CANDIDATES
    }
    assert all(product.food_kind == "ingredient" for product in products)
    assert all("FODMAP por validar" in (product.description or "") for product in products)
    assert all(product.source_reference.startswith("https://") for product in products)
    assert all(product.compositions == [] for product in products)

    profiles = list(db_session.scalars(
        select(FoodTransformationProfile).where(
            FoodTransformationProfile.family_id == family.id,
            FoodTransformationProfile.substitution_group == GROUP,
        )
    ).all())
    assert len(profiles) == len(CANDIDATES) + 1
    assert all(not profile.auto_transform_enabled for profile in profiles)
    assert db_session.scalar(
        select(func.count(FoodCompositionSnapshot.id)).join(FoodItem).where(
            FoodItem.source == SOURCE
        )
    ) == 0

    recipe = db_session.scalar(select(Recipe).where(
        Recipe.recipe_key == "breakfast:recipe:coffee-milk-butter-toast"
    ))
    assert recipe is not None
    variants, _ = _load_variants(db_session, family_id=family.id, recipe=recipe)
    assert all(variant.operation.substitution_group != GROUP for variant in variants)


def test_retail_bread_catalogue_does_not_override_family_settings(
    db_session: Session,
) -> None:
    family = Family(name="Família com preferências", timezone="Europe/Lisbon")
    db_session.add(family)
    db_session.flush()
    seed_development_breakfast_catalog(db_session, families=(family,))
    seed_development_bread_candidates(db_session, families=(family,))
    item = db_session.scalar(
        select(FoodItem).where(FoodItem.catalog_key == SOURCE_BREAD_KEY)
    )
    assert item is not None
    profile = db_session.scalar(select(FoodTransformationProfile).where(
        FoodTransformationProfile.family_id == family.id,
        FoodTransformationProfile.food_item_id == item.id,
    ))
    assert profile is not None
    profile.auto_transform_enabled = True
    profile.typical_quantity = 35
    db_session.flush()

    seed_development_bread_candidates(db_session, families=(family,))
    db_session.refresh(profile)
    assert profile.auto_transform_enabled is True
    assert profile.typical_quantity == 35

    product = db_session.scalar(
        select(FoodItem).where(FoodItem.catalog_key == CANDIDATES[0].key)
    )
    assert product is not None
    original_name = product.name
    product.name = "Nome revisto pela família"
    db_session.flush()
    seed_development_bread_candidates(db_session, families=(family,))
    db_session.refresh(product)
    assert product.name == "Nome revisto pela família"
    assert product.name != original_name
