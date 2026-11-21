from sqlalchemy import select
from sqlalchemy.orm import Session

from app.development_breakfast_seed import seed_development_breakfast_catalog
from app.development_plant_milk_seed import (
    GROUP,
    OPTIONS,
    seed_development_plant_milk_options,
)
from app.models.family import Family
from app.models.food_catalog import FoodItem, Recipe
from app.models.food_transformation_profile import FoodTransformationProfile
from app.services.shared_meal_transformation import _load_variants


def test_milk_alternatives_are_idempotent_and_reusable_for_breakfast(
    db_session: Session,
) -> None:
    family = Family(name="Família alternativa", timezone="Europe/Lisbon")
    db_session.add(family)
    db_session.flush()
    seed_development_breakfast_catalog(db_session, families=(family,))
    assert seed_development_plant_milk_options(
        db_session, families=(family,)
    ) == (len(OPTIONS), 2)
    assert seed_development_plant_milk_options(
        db_session, families=(family,)
    ) == (len(OPTIONS), 2)
    db_session.flush()

    profiles = list(db_session.scalars(
        select(FoodTransformationProfile).where(
            FoodTransformationProfile.family_id == family.id,
            FoodTransformationProfile.substitution_group == GROUP,
        )
    ).all())
    assert len(profiles) == len(OPTIONS)
    enabled = {db_session.get(FoodItem, profile.food_item_id).catalog_key
               for profile in profiles if profile.auto_transform_enabled}
    assert enabled == {
        "breakfast:ingredient:milk", "plant-milk:rice", "plant-milk:lactose-free",
    }
    recipe = db_session.scalar(select(Recipe).where(
        Recipe.recipe_key == "breakfast:recipe:coffee-milk-butter-toast"
    ))
    assert recipe is not None
    db_session.refresh(recipe)
    variants, limitations = _load_variants(db_session, family_id=family.id, recipe=recipe)
    assert {variant.operation.replacement_food_name for variant in variants} == {
        "Bebida vegetal de arroz sem adição de açúcar",
        "Leite meio-gordo sem lactose",
    }
    assert not limitations
