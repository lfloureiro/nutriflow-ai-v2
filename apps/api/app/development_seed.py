from sqlalchemy import delete

from app.commercial_demo_seed import COMMERCIAL_DEMO_REFERENCE
from app.db.session import SessionLocal
from app.demo_nutrition_target_seed import seed_demo_nutrition_targets
from app.demo_seed import seed_demo_dataset
from app.development_breakfast_seed import seed_development_breakfast_catalog
from app.development_legacy_recipe_planning_seed import (
    seed_development_legacy_recipe_planning_catalog,
)
from app.development_planning_profile_seed import seed_development_planning_profiles
from app.development_snack_seed import seed_development_snack_catalog
from app.legacy_v1_loureiro_seed import seed_loureiro_v1_snapshot
from app.models.family import Family
from app.models.meal_candidate_availability import (
    MealCandidateAvailability,
    MealCommercialOffer,
)


def _remove_fake_commercial_browser_data(session) -> None:
    session.execute(
        delete(MealCommercialOffer).where(
            MealCommercialOffer.source_reference == COMMERCIAL_DEMO_REFERENCE
        )
    )
    session.execute(
        delete(MealCandidateAvailability).where(
            MealCandidateAvailability.source_reference == COMMERCIAL_DEMO_REFERENCE
        )
    )


def _configure_loureiro_meal_sources(family: Family) -> None:
    family.meal_discovery_sources = list(
        dict.fromkeys([*family.meal_discovery_sources, "shared_recipes", "restaurants"])
    )
    if not (family.restaurant_area or "").strip():
        family.restaurant_area = "Lisboa"


def main() -> None:
    with SessionLocal() as session:
        demo = seed_demo_dataset(session)
        session.flush()
        demo_family = session.get(Family, demo.family_id)
        if demo_family is None:
            raise RuntimeError("Development demo Family could not be loaded.")

        nutrition = seed_demo_nutrition_targets(session)
        loureiro = seed_loureiro_v1_snapshot(session)
        loureiro_family = session.get(Family, loureiro.family_id)
        if loureiro_family is None:
            raise RuntimeError("Família Loureiro could not be loaded after v1 import.")
        _configure_loureiro_meal_sources(loureiro_family)
        legacy_planning = seed_development_legacy_recipe_planning_catalog(session)

        breakfasts = seed_development_breakfast_catalog(
            session,
            families=(demo_family, loureiro_family),
        )
        snacks = seed_development_snack_catalog(
            session,
            families=(demo_family, loureiro_family),
        )
        _remove_fake_commercial_browser_data(session)
        planning = seed_development_planning_profiles(session, family=demo_family)
        session.commit()

    print("NutriFlow complete development dataset ready.")
    print(f"Technical demo Family ID: {demo.family_id}")
    print(f"Família Loureiro ID: {loureiro.family_id}")
    print(f"Planning date: {demo.planning_date.isoformat()}")
    print(f"Technical demo members: {demo.member_count}")
    print(f"Família Loureiro members: {loureiro.member_count}")
    print(f"Real v1 recipe ingredients used: {loureiro.ingredient_count}")
    print(f"Real v1 shared recipes: {loureiro.recipe_count}")
    print(f"Planning-visible real v1 shared recipes: {legacy_planning.recipe_count}")
    print(f"Família Loureiro v1 ratings: {loureiro.rating_count}")
    print(f"Shared breakfast recipes: {breakfasts.recipe_count}")
    print(f"Shared breakfast ingredients: {breakfasts.ingredient_count}")
    print(f"Shared snack recipes: {snacks.recipe_count}")
    print(f"New shared snack ingredients: {snacks.new_ingredient_count}")
    print(f"Demo nutrition targets: {nutrition.target_count}")
    print(f"Demo calorie budget states: {nutrition.state_count}")
    print("Família Loureiro meal sources: shared recipes + live restaurants")
    print("Commercial demo providers: removed/disabled")
    print(f"Planning profiles: {planning.profile_count}")


if __name__ == "__main__":
    main()
