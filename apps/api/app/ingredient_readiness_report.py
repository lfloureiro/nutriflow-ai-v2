import argparse

from app.db.session import SessionLocal
from app.services.ingredient_readiness_report import (
    BLOCKER_MISSING_CONVERSION,
    IngredientBlockerPriority,
    IngredientReadinessReport,
    build_ingredient_readiness_report,
)


def _format_priority(item: IngredientBlockerPriority) -> str:
    detail = ""
    if item.blocker_type == BLOCKER_MISSING_CONVERSION:
        detail = f" | {item.recipe_unit}->{item.reference_unit}"
    return (
        f"{item.blocker_type} | {item.ingredient_name}{detail} | "
        f"recipes={item.affected_recipe_count} | "
        f"occurrences={item.occurrence_count} | "
        f"sole_unlocks={item.sole_blocker_recipe_count}"
    )


def _print_report(report: IngredientReadinessReport, *, top: int) -> None:
    for item in report.recipes:
        print(item.recipe_name)
        print(
            f"  status={item.status} | ingredients={item.ingredient_count} | "
            f"quantitative={item.quantitative_count} | "
            f"ready={item.ready_quantitative_count} | "
            f"qualitative={item.qualitative_count} | "
            f"estimated_conversions={item.estimated_conversion_count}"
        )
        print(
            "  blockers: "
            f"composition={item.missing_composition_count} | "
            f"energy={item.missing_energy_count} | "
            f"conversion={item.missing_conversion_count} | "
            f"total={item.blocker_count}"
        )
        print()

    print("SUMMARY")
    print(f"recipes={len(report.recipes)}")
    print(f"ready={report.ready_recipe_count}")
    print(f"blocked={report.blocked_recipe_count}")
    print(f"no_ingredients={report.no_ingredients_recipe_count}")
    print()

    print("PRIORITIES")
    for index, item in enumerate(report.priorities[: max(top, 0)], 1):
        print(f"{index}. {_format_priority(item)}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only ingredient nutrition readiness report for legacy recipes. "
            "No web calls or database writes are performed."
        )
    )
    parser.add_argument(
        "--top",
        type=int,
        default=30,
        help="Maximum number of blocker priorities to display.",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        report = build_ingredient_readiness_report(db)
    finally:
        db.close()

    _print_report(report, top=args.top)


if __name__ == "__main__":
    main()
