import argparse
import json
from dataclasses import asdict
from pathlib import Path

from app.db.session import SessionLocal
from app.services.portfir import download_portfir_workbook, load_portfir_foods
from app.services.portfir_enrichment import auto_enrich_shared_ingredients_from_portfir

DEFAULT_CACHE_PATH = Path(".cache/portfir/insa_tca.xlsx")


def _workbook_path(args: argparse.Namespace) -> Path:
    if args.workbook is not None:
        return Path(args.workbook)
    path = DEFAULT_CACHE_PATH
    if args.refresh or not path.is_file():
        download_portfir_workbook(path)
    return path


def _auto_command(args: argparse.Namespace) -> None:
    foods = load_portfir_foods(_workbook_path(args))
    with SessionLocal() as db:
        if args.apply:
            with db.begin():
                result = auto_enrich_shared_ingredients_from_portfir(
                    db,
                    foods=foods,
                    apply=True,
                    limit=args.limit,
                )
        else:
            result = auto_enrich_shared_ingredients_from_portfir(
                db,
                foods=foods,
                apply=False,
                limit=args.limit,
            )
    print(json.dumps([asdict(item) for item in result], ensure_ascii=False, indent=2, default=str))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Automatically enrich shared NutriFlow ingredients from trusted sources."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    auto = subparsers.add_parser(
        "portfir-auto",
        help="Match shared ingredients against PortFIR 7.1 and optionally apply safe matches.",
    )
    auto.add_argument("--workbook")
    auto.add_argument("--refresh", action="store_true")
    auto.add_argument("--apply", action="store_true")
    auto.add_argument("--limit", type=int, default=200, choices=range(1, 1001))
    auto.set_defaults(handler=_auto_command)
    return parser


def main() -> None:
    args = _parser().parse_args()
    args.handler(args)


if __name__ == "__main__":
    main()
