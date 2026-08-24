import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.session import SessionLocal
from app.models.food_catalog import FoodCompositionSnapshot, FoodItem
from app.services.fooddata_central import fetch_food_nutrition, search_foods
from app.services.shared_ingredient_enrichment import (
    apply_fdc_nutrition_to_shared_ingredient,
)


def _missing_shared_ingredients(db: Session, *, limit: int) -> list[dict[str, str]]:
    items = db.scalars(
        select(FoodItem)
        .options(selectinload(FoodItem.compositions))
        .where(
            FoodItem.family_id.is_(None),
            FoodItem.food_kind == "ingredient",
            FoodItem.is_active.is_(True),
        )
        .order_by(FoodItem.name, FoodItem.id)
    ).all()

    result: list[dict[str, str]] = []
    for item in items:
        latest: FoodCompositionSnapshot | None = (
            item.compositions[-1] if item.compositions else None
        )
        if latest is not None and latest.energy_kcal is not None:
            continue
        result.append({"catalog_key": item.catalog_key, "name": item.name})
        if len(result) >= limit:
            break
    return result


def _read_matches(path: Path) -> list[tuple[str, int]]:
    payload: Any = json.loads(path.read_text(encoding="utf-8"))
    raw_matches = payload.get("matches") if isinstance(payload, dict) else payload
    if not isinstance(raw_matches, list):
        raise ValueError("Mapping must be a list or an object containing a matches list.")

    matches: list[tuple[str, int]] = []
    for raw in raw_matches:
        if not isinstance(raw, dict):
            raise ValueError("Each mapping entry must be an object.")
        catalog_key = raw.get("catalog_key")
        fdc_id = raw.get("fdc_id")
        if not isinstance(catalog_key, str) or not catalog_key.strip():
            raise ValueError("Each mapping entry requires catalog_key.")
        if isinstance(fdc_id, bool) or not isinstance(fdc_id, int) or fdc_id <= 0:
            raise ValueError("Each mapping entry requires a positive integer fdc_id.")
        matches.append((catalog_key.strip(), fdc_id))
    return matches


def _search_command(args: argparse.Namespace) -> None:
    results = [asdict(item) for item in search_foods(args.query, limit=args.limit)]
    print(json.dumps(results, ensure_ascii=False, indent=2))


def _list_missing_command(args: argparse.Namespace) -> None:
    with SessionLocal() as db:
        result = _missing_shared_ingredients(db, limit=args.limit)
    print(json.dumps(result, ensure_ascii=False, indent=2))


def _apply_map_command(args: argparse.Namespace) -> None:
    matches = _read_matches(Path(args.path))
    applied: list[dict[str, object]] = []
    with SessionLocal() as db, db.begin():
        for catalog_key, fdc_id in matches:
            food = fetch_food_nutrition(fdc_id)
            result = apply_fdc_nutrition_to_shared_ingredient(
                db,
                catalog_key=catalog_key,
                food=food,
            )
            applied.append(
                {
                    "catalog_key": result.catalog_key,
                    "fdc_id": fdc_id,
                    "composition_id": str(result.composition_id),
                    "data_version": result.data_version,
                    "created": result.created,
                    "recalculated_recipes": len(result.recalculated_recipe_ids),
                }
            )
    print(json.dumps(applied, ensure_ascii=False, indent=2))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Curate shared ingredient nutrition from USDA FoodData Central."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    search = subparsers.add_parser("search", help="Search generic FDC foods.")
    search.add_argument("query")
    search.add_argument("--limit", type=int, default=10, choices=range(1, 26))
    search.set_defaults(handler=_search_command)

    missing = subparsers.add_parser(
        "list-missing",
        help="List shared ingredients that still lack kcal evidence.",
    )
    missing.add_argument("--limit", type=int, default=100)
    missing.set_defaults(handler=_list_missing_command)

    apply_map = subparsers.add_parser(
        "apply-map",
        help="Apply an explicitly approved catalog_key to FDC ID mapping.",
    )
    apply_map.add_argument("path")
    apply_map.set_defaults(handler=_apply_map_command)
    return parser


def main() -> None:
    args = _parser().parse_args()
    args.handler(args)


if __name__ == "__main__":
    main()
