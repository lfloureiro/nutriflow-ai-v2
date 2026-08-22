from app.db.session import SessionLocal
from app.demo_seed import seed_demo_dataset
from app.legacy_v1_demo_seed import seed_legacy_v1_demo_catalog
from app.models.family import Family


def main() -> None:
    with SessionLocal() as session:
        demo = seed_demo_dataset(session)
        session.flush()
        family = session.get(Family, demo.family_id)
        if family is None:
            raise RuntimeError("Development demo Family could not be loaded.")
        legacy = seed_legacy_v1_demo_catalog(session, family=family)
        session.commit()

    print("NutriFlow complete development dataset ready.")
    print(f"Family ID: {demo.family_id}")
    print(f"Planning date: {demo.planning_date.isoformat()}")
    print(f"Members: {demo.member_count}")
    print(f"Demo meal candidates: {demo.candidate_count}")
    print(f"Legacy v1 ingredients: {legacy.ingredient_count}")
    print(f"Legacy v1 recipes: {legacy.recipe_count}")


if __name__ == "__main__":
    main()
