import argparse

from app.db.session import SessionLocal
from app.services.practical_nutrition_profile import build_practical_nutrition_profile
from app.services.recipe_structure_profile import load_legacy_recipes_for_structure


def _names(values: tuple[str, ...]) -> str:
    return " | ".join(values) if values else "-"


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only practical nutrition report focused on the main protein, "
            "carbohydrates, vegetables, energy-dense modifiers and cooking method."
        )
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional maximum number of recipes to display.",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        recipes = load_legacy_recipes_for_structure(db)
        if args.limit is not None:
            recipes = recipes[: max(args.limit, 0)]
        profiles = tuple(build_practical_nutrition_profile(recipe) for recipe in recipes)
    finally:
        db.close()

    for profile in profiles:
        print(profile.recipe_name)
        print(f"  cooking={profile.cooking_method}")
        print(
            f"  protein={profile.primary_protein or '-'} "
            f"({profile.protein_pattern})"
        )
        print(f"  secondary_protein={_names(profile.secondary_proteins)}")
        print(
            f"  carbohydrate={profile.primary_carbohydrate or '-'} "
            f"({profile.carbohydrate_pattern})"
        )
        print(f"  other_carbohydrates={_names(profile.other_carbohydrates)}")
        print(
            f"  vegetables={_names(profile.vegetables)} "
            f"({profile.vegetable_level})"
        )
        if profile.modifiers:
            modifier_text = " | ".join(
                f"{item.name}={item.quantity} {item.unit} "
                f"[{item.kind}:{item.load}]"
                for item in profile.modifiers
            )
            print(f"  modifiers={modifier_text}")
        else:
            print("  modifiers=-")
        print(f"  energy_load={profile.energy_load_signal}")
        print(f"  balance={_names(profile.balance_signals)}")
        print(f"  calorie_drivers={_names(profile.calorie_drivers)}")
        print()

    print("SUMMARY")
    print(f"recipes={len(profiles)}")
    print(
        "energy_load_high="
        f"{sum(item.energy_load_signal == 'high' for item in profiles)}"
    )
    print(
        "structurally_balanced="
        f"{sum('structurally_balanced' in item.balance_signals for item in profiles)}"
    )
    print(
        "vegetables_missing="
        f"{sum(item.vegetable_level == 'none' for item in profiles)}"
    )


if __name__ == "__main__":
    main()
