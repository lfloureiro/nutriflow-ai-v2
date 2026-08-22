from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.commercial_demo_seed import seed_commercial_demo_catalog
from app.demo_seed import DEMO_FAMILY_ID, DEMO_FOODS, seed_demo_dataset
from app.models.family import Family
from app.models.food_catalog import FoodCompositionSnapshot
from app.services.commercial_availability import build_commercial_planning_context
from app.services.meal_recommendation import build_food_candidate

NOW = datetime(2026, 8, 22, 18, 30, tzinfo=UTC)


def test_commercial_demo_seed_is_idempotent_and_exposes_delivery_and_restaurant(
    db_session: Session,
) -> None:
    seed_demo_dataset(db_session, now=NOW)
    db_session.flush()
    family = db_session.get(Family, DEMO_FAMILY_ID)
    assert family is not None

    first = seed_commercial_demo_catalog(db_session, family=family, now=NOW)
    second = seed_commercial_demo_catalog(db_session, family=family, now=NOW)
    db_session.flush()

    assert first == second
    assert first.availability_count == len(DEMO_FOODS) * 2
    assert first.offer_count == len(DEMO_FOODS) * 3

    food = DEMO_FOODS[0]
    composition = db_session.scalar(
        select(FoodCompositionSnapshot)
        .where(FoodCompositionSnapshot.food_item_id == food.id)
        .order_by(FoodCompositionSnapshot.effective_at.desc())
        .limit(1)
    )
    assert composition is not None
    candidate = build_food_candidate(
        composition,
        quantity=composition.reference_quantity,
        quantity_unit=composition.reference_unit,
    )

    delivery = build_commercial_planning_context(
        db_session,
        family_id=DEMO_FAMILY_ID,
        candidates=[candidate],
        scheduled_at=NOW,
        source_kinds=frozenset({"delivery"}),
    )
    assert delivery.practical_profiles[0].is_available is True
    assert {offer.provider_name for offer in delivery.offers} == {
        "Glovo (demo)",
        "Uber Eats (demo)",
    }
    assert all(offer.total_known_price > Decimal(0) for offer in delivery.offers)

    restaurant = build_commercial_planning_context(
        db_session,
        family_id=DEMO_FAMILY_ID,
        candidates=[candidate],
        scheduled_at=NOW,
        source_kinds=frozenset({"restaurant"}),
    )
    assert restaurant.practical_profiles[0].is_available is True
    assert [offer.provider_name for offer in restaurant.offers] == [
        "Restaurante Lisboa (demo)"
    ]
