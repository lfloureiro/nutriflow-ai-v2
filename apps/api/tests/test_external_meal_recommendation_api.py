import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.main import app
from app.models.family import Family
from app.models.food_preference import FoodPreference
from app.models.nutrition_constraint import NutritionConstraint
from app.models.nutrition_plan import NutritionPlan, NutritionPlanRule
from app.models.person import Person
from app.schemas.external_menu import (
    ExternalMenuItemObservationWrite,
    ExternalMenuNutrientWrite,
    ExternalMenuNutritionWrite,
)
from app.services.external_menu_ingestion import ingest_external_menu_item

PLANNING_DATE = date(2026, 9, 16)
SCHEDULED_AT = datetime(2026, 9, 16, 12, 0, tzinfo=UTC)
OBSERVED_AT = SCHEDULED_AT - timedelta(minutes=30)


def _override_db(db_session: Session):
    def override_get_db():
        yield db_session

    return override_get_db


def _observation(
    *,
    item_key: str,
    item_name: str,
    protein: str | None,
    price: str,
) -> ExternalMenuItemObservationWrite:
    nutrition = None
    if protein is not None:
        nutrition = ExternalMenuNutritionWrite(
            evidence_level="provider",
            reference_quantity=Decimal(1),
            reference_unit="serving",
            energy_kcal=Decimal(550),
            nutrients=[
                ExternalMenuNutrientWrite(
                    key="protein",
                    value=Decimal(protein),
                    unit="g",
                )
            ],
        )
    return ExternalMenuItemObservationWrite(
        provider_key="delivery-test",
        provider_name="Delivery Test",
        merchant_key="merchant-1",
        merchant_name="Restaurante Teste",
        item_key=item_key,
        item_name=item_name,
        description=f"Menu item {item_name}",
        source_kind="delivery",
        location="Lisboa",
        item_price=Decimal(price),
        currency="EUR",
        delivery_fee=Decimal("1.50"),
        observed_at=OBSERVED_AT,
        valid_until=SCHEDULED_AT + timedelta(hours=2),
        source_reference=f"https://example.invalid/{item_key}",
        nutrition=nutrition,
    )


def _family_person(db_session: Session) -> tuple[Family, Person]:
    family = Family(name="External Plan-Fit family", timezone="Europe/Lisbon")
    person = Person(
        family=family,
        first_name="Ana",
        preferred_locale="pt-PT",
        timezone="Europe/Lisbon",
    )
    db_session.add(family)
    db_session.flush()
    return family, person


def _protein_plan(person: Person) -> NutritionPlan:
    constraint = NutritionConstraint(
        person=person,
        constraint_type="meal_target",
        target_type="nutrient",
        target_key="protein",
        operator="min",
        value_min=Decimal("15.0000"),
        unit="g",
        severity="required",
        is_mandatory=True,
        source="nutritionist",
        start_date=PLANNING_DATE,
    )
    return NutritionPlan(
        person=person,
        lineage_id=uuid.uuid4(),
        version=1,
        title="Lunch protein plan",
        source_type="nutritionist",
        source_name="Test nutritionist",
        status="active",
        valid_from=PLANNING_DATE,
        rules=[
            NutritionPlanRule(
                rule_kind="constraint",
                nutrition_constraint=constraint,
                meal_type="lunch",
                priority=120,
                source_statement="Lunch protein at least 15 g.",
                applies_outside_plan=False,
            )
        ],
    )


def _post(db_session: Session, person: Person, payload: dict[str, object]):
    app.dependency_overrides[get_db] = _override_db(db_session)
    try:
        with TestClient(app) as client:
            return client.post(
                f"/api/persons/{person.id}/meal-recommendations/external",
                json=payload,
            )
    finally:
        app.dependency_overrides.clear()


def test_external_recommendation_discovers_normalized_items_and_uses_plan_fit(
    db_session: Session,
) -> None:
    family, person = _family_person(db_session)
    db_session.add(_protein_plan(person))
    db_session.flush()

    low = ingest_external_menu_item(
        db_session,
        family=family,
        data=_observation(
            item_key="low-protein",
            item_name="Preferred low protein bowl",
            protein="10",
            price="8.50",
        ),
    )
    high = ingest_external_menu_item(
        db_session,
        family=family,
        data=_observation(
            item_key="high-protein",
            item_name="High protein bowl",
            protein="25",
            price="12.00",
        ),
    )
    missing = ingest_external_menu_item(
        db_session,
        family=family,
        data=_observation(
            item_key="missing-nutrition",
            item_name="Unknown nutrition bowl",
            protein=None,
            price="7.00",
        ),
    )
    person.food_preferences.append(
        FoodPreference(
            subject_type="food",
            subject_key=low.catalog_key,
            preference_type="like",
            intensity=5,
            source="user",
        )
    )
    db_session.flush()

    response = _post(
        db_session,
        person,
        {
            "scheduled_at": SCHEDULED_AT.isoformat(),
            "meal_type": "lunch",
            "source_kinds": ["delivery"],
            "delivery_provider_keys": ["delivery-test"],
            "max_results": None,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["planning_date"] == PLANNING_DATE.isoformat()
    assert body["discovered_count"] == 3
    assert body["evaluated_count"] == 2

    evidence = {item["catalog_key"]: item for item in body["evidence"]}
    assert evidence[high.catalog_key]["evaluated"] is True
    assert evidence[high.catalog_key]["nutrition_evidence_level"] == "provider"
    assert evidence[missing.catalog_key]["evaluated"] is False
    assert evidence[missing.catalog_key]["reason"] == "nutrition_composition_missing"
    assert evidence[missing.catalog_key]["composition_id"] is None

    recommendation = body["recommendation"]
    assert recommendation is not None
    assert recommendation["engine_version"] == (
        "meal-recommendation-practical-plan-fit-v1+diversity-v1"
    )
    options = {option["candidate_key"]: option for option in recommendation["options"]}
    assert options[high.catalog_key]["eligible"] is True
    assert options[high.catalog_key]["rank"] == 1
    assert options[high.catalog_key]["score_breakdown"]["plan_fit"] == "1.0000"

    assert options[low.catalog_key]["eligible"] is False
    assert options[low.catalog_key]["rank"] is None
    assert "plan_fit_rule:meal:nutrient:protein:fail" in options[low.catalog_key][
        "exclusion_reasons"
    ]
    assert "plan_fit_status:fail" in options[low.catalog_key]["exclusion_reasons"]


def test_external_recommendation_keeps_missing_nutrition_out_of_scoring(
    db_session: Session,
) -> None:
    family, person = _family_person(db_session)
    missing = ingest_external_menu_item(
        db_session,
        family=family,
        data=_observation(
            item_key="missing-only",
            item_name="No nutrition available",
            protein=None,
            price="9.00",
        ),
    )
    db_session.flush()

    response = _post(
        db_session,
        person,
        {
            "scheduled_at": SCHEDULED_AT.isoformat(),
            "meal_type": "lunch",
            "source_kinds": ["delivery"],
            "delivery_provider_keys": ["delivery-test"],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["discovered_count"] == 1
    assert body["evaluated_count"] == 0
    assert body["recommendation"] is None
    assert body["evidence"][0]["catalog_key"] == missing.catalog_key
    assert body["evidence"][0]["evaluated"] is False
    assert body["evidence"][0]["reason"] == "nutrition_composition_missing"
