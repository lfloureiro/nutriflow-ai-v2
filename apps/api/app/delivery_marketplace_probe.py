import argparse

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.family import Family
from app.providers.apify_delivery import (
    GlovoApifyAdapter,
    UberEatsApifyAdapter,
    apify_delivery_configured,
)
from app.providers.meal_delivery import MealDeliveryDiscoveryRequest


def _adapter(provider: str):
    if provider == "uber_eats":
        return UberEatsApifyAdapter()
    if provider == "glovo":
        return GlovoApifyAdapter()
    raise ValueError(f"Unsupported provider: {provider}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Probe a live public delivery marketplace without writing to the database."
    )
    parser.add_argument(
        "--provider",
        choices=("uber_eats", "glovo"),
        required=True,
    )
    parser.add_argument("--query", default=None)
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--family", default="Família Loureiro")
    args = parser.parse_args()

    if not apify_delivery_configured():
        raise SystemExit(
            "Apify delivery discovery is not configured in this process. "
            "Set the existing NUTRIFLOW_APIFY_API_TOKEN securely before running the probe."
        )

    with SessionLocal() as db:
        family = db.scalar(select(Family).where(Family.name == args.family))
        if family is None:
            raise SystemExit(f"Family not found: {args.family}")
        delivery_address = (family.delivery_address or family.restaurant_area or "").strip()
        if not delivery_address:
            raise SystemExit("The Family has no delivery address or restaurant area configured.")

    observations = _adapter(args.provider).discover_menu_items(
        MealDeliveryDiscoveryRequest(
            delivery_address=delivery_address,
            query=args.query,
            limit=args.limit,
        )
    )

    print(f"provider={args.provider}")
    print(f"address={delivery_address}")
    print(f"query={args.query or '-'}")
    print(f"items={len(observations)}")
    print()
    for item in observations:
        delivery = "" if item.delivery_fee is None else f" + delivery {item.delivery_fee}"
        print(
            f"{item.merchant_name} | {item.item_name} | "
            f"{item.item_price} {item.currency}{delivery}"
        )


if __name__ == "__main__":
    main()
