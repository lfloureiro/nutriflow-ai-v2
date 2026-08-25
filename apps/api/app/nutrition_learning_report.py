import argparse
from decimal import Decimal

from app.db.session import SessionLocal
from app.services.nutrition_learning_report import (
    NutritionLearningDiagnosticReport,
    RecipeLearningDiagnostic,
    build_nutrition_learning_diagnostic_report,
)


def _format_decimal(value: Decimal | None) -> str:
    if value is None:
        return "-"
    return format(value.normalize(), "f")


def _format_recipe(item: RecipeLearningDiagnostic) -> str:
    estimate = _format_decimal(item.estimate_kcal_per_serving)
    interval = "-"
    if item.lower_kcal_per_serving is not None and item.upper_kcal_per_serving is not None:
        interval = (
            f"{_format_decimal(item.lower_kcal_per_serving)}-"
            f"{_format_decimal(item.upper_kcal_per_serving)}"
        )
    servings = _format_decimal(item.serving_count)
    similarity = _format_decimal(item.mean_similarity)
    confidence = item.confidence or "-"
    return (
        f"{item.recipe_name}\n"
        f"  status={item.status} | ingredients={item.ingredient_count} | "
        f"servings={servings} | anomalies={item.anomaly_count}\n"
        f"  google={item.search_hit_count} | structured={item.structured_page_count} | "
        f"failed={item.failed_page_count} | evidence={item.evidence_count} | "
        f"accepted={item.accepted_count}\n"
        f"  estimate={estimate} kcal/dose | range={interval} | "
        f"retained={item.retained_source_count} | similarity={similarity} | "
        f"confidence={confidence}"
    )


def _print_report(report: NutritionLearningDiagnosticReport) -> None:
    for item in report.recipes:
        print(_format_recipe(item))
        for anomaly in item.anomalies:
            print(
                "  ANOMALY: "
                f"{anomaly.ingredient_name}={_format_decimal(anomaly.quantity)} "
                f"{anomaly.unit}; median={_format_decimal(anomaly.group_median)}; "
                f"ratio={_format_decimal(anomaly.ratio_to_median)}x"
            )
        if item.error:
            print(f"  ERROR: {item.error}")
        print()

    print("SUMMARY")
    print(f"recipes={len(report.recipes)}")
    for status, count in sorted(report.status_counts.items()):
        print(f"{status}={count}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only nutrition-learning diagnostic for legacy recipes. "
            "No database values are modified."
        )
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of recipes to inspect.",
    )
    parser.add_argument(
        "--offset",
        type=int,
        default=0,
        help="Number of alphabetically sorted recipes to skip.",
    )
    parser.add_argument(
        "--max-results",
        type=int,
        default=10,
        help="Maximum Google results requested per recipe (1-20).",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        report = build_nutrition_learning_diagnostic_report(
            db,
            max_results=args.max_results,
            offset=args.offset,
            limit=args.limit,
        )
    finally:
        db.close()

    _print_report(report)


if __name__ == "__main__":
    main()
