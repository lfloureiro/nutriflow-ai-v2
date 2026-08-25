import argparse

from app.db.session import SessionLocal
from app.services.recipe_structure_profile import (
    RecipeStructureProfile,
    build_legacy_recipe_structure_profiles,
)


def _names(values: tuple[str, ...]) -> str:
    return " | ".join(values) if values else "-"


def _driver_text(profile: RecipeStructureProfile) -> str:
    values = [
        f"{item.name}={item.quantity} {item.unit}"
        for item in profile.ingredients
        if item.major_calorie_driver
    ]
    return " | ".join(values) if values else "-"


def _print_profile(profile: RecipeStructureProfile) -> None:
    print(profile.recipe_name)
    print(f"  cooking={profile.cooking_method}")
    print(f"  protein={profile.primary_protein or '-'}")
    print(f"  secondary_protein={_names(profile.secondary_proteins)}")
    print(f"  carbohydrate={profile.primary_carbohydrate or '-'}")
    print(f"  other_carbohydrates={_names(profile.other_carbohydrates)}")
    print(f"  vegetables={_names(profile.vegetables)}")
    print(f"  energy_modifiers={_names(profile.energy_modifiers)}")
    print(f"  accessories={_names(profile.accessories)}")
    print(f"  other={_names(profile.other_ingredients)}")
    print(f"  calorie_drivers={_driver_text(profile)}")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only practical nutrition structure report. Focuses on the main protein, "
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
        profiles = build_legacy_recipe_structure_profiles(db)
    finally:
        db.close()

    if args.limit is not None:
        profiles = profiles[: max(args.limit, 0)]

    for profile in profiles:
        _print_profile(profile)

    print("SUMMARY")
    print(f"recipes={len(profiles)}")
    protein_count = sum(item.primary_protein is not None for item in profiles)
    carbohydrate_count = sum(
        item.primary_carbohydrate is not None for item in profiles
    )
    cooking_count = sum(item.cooking_method != "unknown" for item in profiles)
    modifier_count = sum(bool(item.energy_modifiers) for item in profiles)
    print(f"protein_identified={protein_count}")
    print(f"carbohydrate_identified={carbohydrate_count}")
    print(f"cooking_method_identified={cooking_count}")
    print(f"with_energy_modifiers={modifier_count}")


if __name__ == "__main__":
    main()
