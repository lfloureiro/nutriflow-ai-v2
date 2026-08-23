from app.db.session import SessionLocal
from app.demo_nutrition_target_seed import seed_demo_nutrition_targets
from app.demo_seed import seed_demo_dataset
from app.development_planning_profile_seed import seed_development_planning_profiles
from app.legacy_v1_demo_seed import seed_legacy_v1_demo_catalog
from app.models.family import Family


def main() -> None:
    with SessionLocal() as session:
        demo = seed_demo_dataset(session)
        session.flush()
        family = session.get(Family, demo.family_id)
        if family is None:
            raise RuntimeError("Development demo Family could not be loaded.")
        nutrition = seed_demo_nutrition_targets(session)
        legacy = seed_legacy_v1_demo_catalog(session, family=family)
        planning = seed_development_planning_profiles(session, family=family)
        session.commit()

    print("NutriFlow complete development dataset ready.")
    print(f"Family ID: {demo.family_id}")
    print(f"Planning date: {demo.planning_date.isoformat()}")
    print(f"Members: {demo.member_count}")
    print(f"Demo meal candidates: {demo.candidate_count}")
    print(f"Demo nutrition targets: {nutrition.target_count}")
    print(f"Demo calorie budget states: {nutrition.state_count}")
    print(f"Shared v1 ingredients: {legacy.ingredient_count}")
    print(f"Shared v1 recipes: {legacy.recipe_count}")
    print("Commercial demo providers: disabled")
    print(f"Planning profiles: {planning.profile_count}")


if __name__ == "__main__":
    main()
