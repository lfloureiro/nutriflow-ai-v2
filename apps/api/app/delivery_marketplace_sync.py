import argparse

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.family import Family
from app.providers.apify_delivery import GlovoApifyAdapter, UberEatsApifyAdapter
from app.services.meal_delivery_sync import sync_meal_delivery_provider


def _adapter(provider: str):
    if provider == "uber_eats":
        return UberEatsApifyAdapter()
    if provider == "glovo":
        return GlovoApifyAdapter()
    raise ValueError(f"Unsupported provider: {provider}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Synchronize a live delivery marketplace query into NutriFlow and enrich "
            "the returned dishes with usable nutrition when possible."
        )
    )
    parser.add_argument(
        "--provider",
        choices=("uber_eats", "glovo"),
        required=True,
    )
    parser.add_argument("--query", default=None)
    parser.add_argument("--limit", type=int, default=30)
    parser.add_argument("--family", default="Família Loureiro")
    args = parser.parse_args()

    with SessionLocal() as db:
        family = db.scalar(select(Family).where(Family.name == args.family))
        if family is None:
            raise SystemExit(f"Family not found: {args.family}")
        delivery_address = (family.delivery_address or family.restaurant_area or "").strip()
        if not delivery_address:
            raise SystemExit("The Family has no delivery address or restaurant area configured.")

        result = sync_meal_delivery_provider(
            db,
            family=family,
            provider_key=args.provider,
            adapter=_adapter(args.provider),
            delivery_address=delivery_address,
            query=args.query,
            limit=args.limit,
        )
        db.commit()

    nutrition_ready = sum(
        item.eligible_for_nutrition_ranking for item in result.ingested
    )
    print(f"provider={result.provider_key}")
    print(f"address={delivery_address}")
    print(f"query={args.query or '-'}")
    print(f"observed={result.observed_count}")
    print(f"ingested={len(result.ingested)}")
    print(f"nutrition_ready={nutrition_ready}")
    print()
    for observation, ingested in zip(result.observations, result.ingested, strict=True):
        nutrition = observation.nutrition
        if nutrition is None:
            nutrition_text = "nutrition=unavailable"
        else:
            nutrition_text = (
                f"nutrition={nutrition.energy_kcal} kcal "
                f"({nutrition.evidence_level}, confidence={nutrition.confidence})"
            )
        print(
            f"{observation.merchant_name} | {observation.item_name} | "
            f"{observation.item_price} {observation.currency} | {nutrition_text} | "
            f"eligible={ingested.eligible_for_nutrition_ranking}"
        )


if __name__ == "__main__":
    main()
