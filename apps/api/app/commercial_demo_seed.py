import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.demo_seed import DEMO_FOODS
from app.models.family import Family
from app.models.food_catalog import FoodItem
from app.models.meal_candidate_availability import (
    MealCandidateAvailability,
    MealCommercialOffer,
)

COMMERCIAL_DEMO_NAMESPACE = uuid.UUID("2f5c8ae9-13da-4f2f-9cae-73a48fece001")
COMMERCIAL_DEMO_SOURCE = "demo"
COMMERCIAL_DEMO_REFERENCE = "nutriflow-development-commercial-demo"


@dataclass(frozen=True)
class CommercialDemoSeedResult:
    availability_count: int
    offer_count: int


@dataclass(frozen=True)
class DemoOfferDefinition:
    provider_key: str
    provider_name: str
    item_price: Decimal
    delivery_fee: Decimal | None
    minimum_order: Decimal | None


DELIVERY_OFFERS = (
    DemoOfferDefinition(
        provider_key="uber-eats-demo",
        provider_name="Uber Eats (demo)",
        item_price=Decimal("12.90"),
        delivery_fee=Decimal("2.49"),
        minimum_order=Decimal("8.00"),
    ),
    DemoOfferDefinition(
        provider_key="glovo-demo",
        provider_name="Glovo (demo)",
        item_price=Decimal("11.90"),
        delivery_fee=Decimal("2.99"),
        minimum_order=Decimal("8.00"),
    ),
)

RESTAURANT_OFFERS = (
    DemoOfferDefinition(
        provider_key="restaurante-lisboa-demo",
        provider_name="Restaurante Lisboa (demo)",
        item_price=Decimal("10.90"),
        delivery_fee=None,
        minimum_order=None,
    ),
)


def _stable_id(kind: str, key: str) -> uuid.UUID:
    return uuid.uuid5(COMMERCIAL_DEMO_NAMESPACE, f"{kind}:{key}")


def _ensure_availability(
    session: Session,
    *,
    family: Family,
    food: FoodItem,
    source_kind: str,
) -> MealCandidateAvailability:
    source_key = f"demo:{source_kind}:{food.catalog_key}"
    availability_id = _stable_id("availability", source_key)
    availability = session.get(MealCandidateAvailability, availability_id)
    if availability is None:
        availability = MealCandidateAvailability(
            id=availability_id,
            family_id=family.id,
            food_item_id=food.id,
            candidate_kind="food_item",
            source_kind=source_kind,
            source_key=source_key,
            location="Lisboa",
            preparation_minutes=25 if source_kind == "delivery" else 15,
            requires_kitchen=False,
            is_available=True,
            source=COMMERCIAL_DEMO_SOURCE,
            source_reference=COMMERCIAL_DEMO_REFERENCE,
            notes="Development-only commercial availability. Not live provider data.",
        )
        session.add(availability)
    else:
        availability.family_id = family.id
        availability.food_item_id = food.id
        availability.recipe_id = None
        availability.candidate_kind = "food_item"
        availability.source_kind = source_kind
        availability.source_key = source_key
        availability.location = "Lisboa"
        availability.preparation_minutes = 25 if source_kind == "delivery" else 15
        availability.requires_kitchen = False
        availability.is_available = True
        availability.source = COMMERCIAL_DEMO_SOURCE
        availability.source_reference = COMMERCIAL_DEMO_REFERENCE
        availability.notes = "Development-only commercial availability. Not live provider data."
    return availability


def _ensure_offer(
    session: Session,
    *,
    family: Family,
    availability: MealCandidateAvailability,
    food: FoodItem,
    source_kind: str,
    definition: DemoOfferDefinition,
    observed_at: datetime,
    price_offset: Decimal,
) -> MealCommercialOffer:
    offer_key = f"demo:{source_kind}:{definition.provider_key}:{food.catalog_key}"
    offer_id = _stable_id("offer", offer_key)
    offer = session.get(MealCommercialOffer, offer_id)
    item_price = definition.item_price + price_offset
    if offer is None:
        offer = MealCommercialOffer(
            id=offer_id,
            family_id=family.id,
            availability=availability,
            offer_key=offer_key,
            provider_key=definition.provider_key,
            provider_name=definition.provider_name,
            item_price=item_price,
            currency="EUR",
            delivery_fee=definition.delivery_fee,
            minimum_order=definition.minimum_order,
            is_available=True,
            valid_from=None,
            valid_until=None,
            observed_at=observed_at,
            source=COMMERCIAL_DEMO_SOURCE,
            source_reference=COMMERCIAL_DEMO_REFERENCE,
            notes="Synthetic development offer. Not a live Uber Eats, Glovo, or restaurant quote.",
        )
        session.add(offer)
    else:
        offer.family_id = family.id
        offer.availability_id = availability.id
        offer.offer_key = offer_key
        offer.provider_key = definition.provider_key
        offer.provider_name = definition.provider_name
        offer.item_price = item_price
        offer.currency = "EUR"
        offer.delivery_fee = definition.delivery_fee
        offer.minimum_order = definition.minimum_order
        offer.is_available = True
        offer.valid_from = None
        offer.valid_until = None
        offer.observed_at = observed_at
        offer.source = COMMERCIAL_DEMO_SOURCE
        offer.source_reference = COMMERCIAL_DEMO_REFERENCE
        offer.notes = "Synthetic development offer. Not a live Uber Eats, Glovo, or restaurant quote."
    return offer


def seed_commercial_demo_catalog(
    session: Session,
    *,
    family: Family,
    now: datetime | None = None,
) -> CommercialDemoSeedResult:
    observed_at = now or datetime.now(UTC)
    if observed_at.tzinfo is None or observed_at.utcoffset() is None:
        raise ValueError("Commercial demo seed instant must be timezone-aware.")
    observed_at = observed_at.astimezone(UTC)

    availability_count = 0
    offer_count = 0
    for index, food_definition in enumerate(DEMO_FOODS):
        food = session.get(FoodItem, food_definition.id)
        if food is None:
            raise RuntimeError(
                f"Demo FoodItem {food_definition.catalog_key!r} must be seeded before commercial offers."
            )
        price_offset = Decimal(index) * Decimal("0.60")
        for source_kind, definitions in (
            ("delivery", DELIVERY_OFFERS),
            ("restaurant", RESTAURANT_OFFERS),
        ):
            availability = _ensure_availability(
                session,
                family=family,
                food=food,
                source_kind=source_kind,
            )
            session.flush()
            availability_count += 1
            for definition in definitions:
                _ensure_offer(
                    session,
                    family=family,
                    availability=availability,
                    food=food,
                    source_kind=source_kind,
                    definition=definition,
                    observed_at=observed_at,
                    price_offset=price_offset,
                )
                offer_count += 1
    session.flush()
    return CommercialDemoSeedResult(
        availability_count=availability_count,
        offer_count=offer_count,
    )
