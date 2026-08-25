import argparse

from app.db.session import SessionLocal
from app.services.recipe_practical_backfill import (
    RecipePracticalBackfillResult,
    backfill_recipe_practical_nutrition,
)


def _energy(value) -> str:
    return "-" if value is None else f"{value.quantize(1)}"


def _print_result(item: RecipePracticalBackfillResult) -> None:
    serving = "-" if item.serving_count is None else str(item.serving_count)
    if item.serving_count_estimated and item.serving_count is not None:
        serving += " estimated"
    confidence = item.confidence or "-"
    balance = " | ".join(item.balance_signals) if item.balance_signals else "-"
    print(item.recipe_name)
    print(
        f"  energy={_energy(item.energy_per_serving_kcal)} kcal/dose | "
        f"total={_energy(item.energy_kcal)} kcal | servings={serving} | "
        f"evidence={item.evidence} | confidence={confidence}"
    )
    print(
        f"  protein={item.primary_protein or '-'} | "
        f"carbohydrate={item.primary_carbohydrate or '-'} | "
        f"vegetables={item.vegetable_level} | energy_load={item.energy_load_signal}"
    )
    print(f"  balance={balance} | issues={item.issue_count}")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Rebuild recipe composition snapshots with practical nutrition classification "
            "and planning energy estimates. Use --dry-run to preview without DB changes."
        )
    )
    parser.add_argument(
        "--prefix",
        default="legacy-v1:",
        help="Recipe key prefix to process. Defaults to the imported legacy recipe set.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview classifications and estimates, then roll back all snapshot writes.",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        results = backfill_recipe_practical_nutrition(
            db,
            recipe_key_prefix=args.prefix,
            commit=not args.dry_run,
        )
    finally:
        db.close()

    if args.dry_run:
        print("DRY RUN - no database changes persisted")
        print()

    for item in results:
        _print_result(item)

    print("SUMMARY")
    print(f"recipes={len(results)}")
    print(f"with_energy={sum(item.energy_per_serving_kcal is not None for item in results)}")
    print(f"estimated={sum(item.evidence == 'practical_estimate' for item in results)}")
    print(f"exact={sum(item.evidence == 'ingredient_calculated' for item in results)}")
    print(f"unavailable={sum(item.energy_per_serving_kcal is None for item in results)}")


if __name__ == "__main__":
    main()
