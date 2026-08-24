from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.family import Family
from app.models.food_catalog import FoodCompositionSnapshot, FoodItem, FoodNutrientComponent
from app.models.meal_candidate_availability import (
    MealCandidateAvailability,
    MealCommercialOffer,
)
from app.models.person import Person
from app.schemas.external_menu import (
    ExternalMenuItemObservationWrite,
    ExternalMenuNutrientWrite,
    ExternalMenuNutritionWrite,
)
from app.services.external_menu_ingestion import ingest_external_menu_item
from app.services.planning_bootstrap_api import get_planning_bootstrap

NOW = datetime(2026, 8, 23, 19, 0, tzinfo=UTC)


def _family(db_session: Session, *, name: str = "Família Menu") -> Family:
    family = Family(name=name, timezone="Europe/Lisbon")
    db_session.add(family)
    db_session.flush()
    return family


def _observation(*, price: str = "12.50", with_nutrition: bool = False):
    return ExternalMenuItemObservationWrite(
        provider_key="restaurant_web",
        provider_name="Restaurant website",
        merchant_key="merchant-123",
        merchant_name="Restaurante Exemplo",
        item_key="dish-456",
        item_name="Frango grelhado com arroz",
        description="Frango, arroz e legumes",
        source_kind="restaurant",
        location="Benfica, Lisboa",
        item_price=Decimal(price),
        currency="EUR",
        observed_at=NOW,
        valid_until=NOW + timedelta(hours=6),
        source_reference="https://example.invalid/menu/dish-456",
        nutrition=(
            ExternalMenuNutritionWrite(
                evidence_level="official",
                reference_quantity=Decimal(1),
                reference_unit="serving",
                energy_kcal=Decimal(640),
                nutrients=[
                    ExternalMenuNutrientWrite(
                        key="protein",
                        value=Decimal(42),
                        unit="g",
                    ),
                    ExternalMenuNutrientWrite(
                        key="sodium",
                        value=Decimal(780),
                        unit="mg",
                    ),
                ],
            )
            if with_nutrition
            else None
        ),
    )


def test_external_menu_item_without_nutrition_is_not_ranking_ready(
    db_session: Session,
) -> None:
    family = _family(db_session)

    first = ingest_external_menu_item(
        db_session,
        family=family,
        data=_observation(),
    )
    second = ingest_external_menu_item(
        db_session,
        family=family,
        data=_observation(price="13.25"),
    )
    db_session.flush()

    assert first.food_item_id == second.food_item_id
    assert first.availability_id == second.availability_id
    assert first.offer_id == second.offer_id
    assert first.composition_id is None
    assert not first.eligible_for_nutrition_ranking

    item = db_session.get(FoodItem, first.food_item_id)
    assert item is not None
    assert item.family_id == family.id
    assert item.food_kind == "dish"
    assert item.brand == "Restaurante Exemplo"

    assert db_session.scalar(select(func.count()).select_from(FoodItem)) == 1
    assert (
        db_session.scalar(select(func.count()).select_from(MealCandidateAvailability)) == 1
    )
    assert db_session.scalar(select(func.count()).select_from(MealCommercialOffer)) == 1
    assert db_session.scalar(select(func.count()).select_from(FoodCompositionSnapshot)) == 0

    offer = db_session.get(MealCommercialOffer, first.offer_id)
    assert offer is not None
    assert offer.item_price == Decimal("13.25")
    assert offer.currency == "EUR"


def test_external_menu_item_with_nutrition_creates_versioned_evidence(
    db_session: Session,
) -> None:
    family = _family(db_session)
    person = Person(
        family=family,
        first_name="Ana",
        preferred_locale="pt-PT",
        timezone="Europe/Lisbon",
    )
    db_session.add(person)
    db_session.flush()

    first = ingest_external_menu_item(
        db_session,
        family=family,
        data=_observation(with_nutrition=True),
    )
    repeated = ingest_external_menu_item(
        db_session,
        family=family,
        data=_observation(with_nutrition=True),
    )
    db_session.flush()

    assert first.eligible_for_nutrition_ranking
    assert first.composition_id is not None
    assert repeated.composition_id == first.composition_id
    assert db_session.scalar(select(func.count()).select_from(FoodCompositionSnapshot)) == 1
    assert db_session.scalar(select(func.count()).select_from(FoodNutrientComponent)) == 2

    composition = db_session.get(FoodCompositionSnapshot, first.composition_id)
    assert composition is not None
    assert composition.reference_quantity == Decimal("1.0000")
    assert composition.reference_unit == "serving"
    assert composition.energy_kcal == Decimal("640.0000")
    assert composition.source == "restaurant_web"
    assert composition.source_reference == "https://example.invalid/menu/dish-456"
    assert composition.notes is not None
    assert '"evidence_level": "official"' in composition.notes

    bootstrap = get_planning_bootstrap(
        db_session,
        person_id=person.id,
        scheduled_at=NOW + timedelta(minutes=1),
    )
    candidate = next(
        item for item in bootstrap.candidates if item.catalog_key == first.catalog_key
    )
    assert candidate.category == "dish"
    assert candidate.energy_kcal == Decimal("640.0000")


def test_external_menu_items_are_isolated_per_family(db_session: Session) -> None:
    first_family = _family(db_session, name="Família A")
    second_family = _family(db_session, name="Família B")
    second_person = Person(
        family=second_family,
        first_name="Bruno",
        preferred_locale="pt-PT",
        timezone="Europe/Lisbon",
    )
    db_session.add(second_person)
    db_session.flush()

    first_item = ingest_external_menu_item(
        db_session,
        family=first_family,
        data=_observation(with_nutrition=True),
    )
    db_session.flush()

    second_bootstrap = get_planning_bootstrap(
        db_session,
        person_id=second_person.id,
        scheduled_at=NOW + timedelta(minutes=1),
    )
    assert all(
        candidate.catalog_key != first_item.catalog_key
        for candidate in second_bootstrap.candidates
    )

    second_item = ingest_external_menu_item(
        db_session,
        family=second_family,
        data=_observation(with_nutrition=True),
    )
    db_session.flush()

    assert second_item.food_item_id != first_item.food_item_id
    assert second_item.catalog_key != first_item.catalog_key

    refreshed = get_planning_bootstrap(
        db_session,
        person_id=second_person.id,
        scheduled_at=NOW + timedelta(minutes=1),
    )
    assert any(
        candidate.catalog_key == second_item.catalog_key
        for candidate in refreshed.candidates
    )