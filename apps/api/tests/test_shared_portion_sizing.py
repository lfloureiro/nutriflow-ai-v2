import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from app.models.daily_nutrition_state import DailyNutritionState
from app.models.food_catalog import FoodCompositionSnapshot, FoodItem
from app.models.person import Person
from app.services.meal_recommendation import build_food_candidate
from app.services.shared_practical_recommendation_api import _candidate_proposals

FAMILY_ID = uuid.UUID("f1111111-1111-4111-8111-111111111111")
ANA_ID = uuid.UUID("a1111111-1111-4111-8111-111111111111")
RUI_ID = uuid.UUID("b1111111-1111-4111-8111-111111111111")


def _person(person_id: uuid.UUID, name: str) -> Person:
    return Person(
        id=person_id,
        family_id=FAMILY_ID,
        first_name=name,
        preferred_locale="pt-PT",
        timezone="Europe/Lisbon",
    )


def _state(person_id: uuid.UUID, minimum: str, maximum: str) -> DailyNutritionState:
    return DailyNutritionState(
        person_id=person_id,
        state_date=date(2026, 8, 23),
        timezone="Europe/Lisbon",
        energy_consumed_kcal=Decimal(0),
        energy_planned_kcal=Decimal(0),
        energy_assumed_kcal=Decimal(0),
        energy_remaining_min_kcal=Decimal(minimum),
        energy_remaining_max_kcal=Decimal(maximum),
        calculation_version="test",
    )


def _candidate():
    food = FoodItem(
        catalog_key="test:shared-meal",
        name="Shared meal",
        food_kind="dish",
        source="test",
    )
    composition = FoodCompositionSnapshot(
        food_item=food,
        reference_quantity=Decimal("1.0000"),
        reference_unit="serving",
        energy_kcal=Decimal("500.00"),
        data_version="test-v1",
        source="test",
        effective_at=datetime(2026, 8, 23, tzinfo=UTC),
    )
    return build_food_candidate(
        composition,
        quantity=Decimal("1.0000"),
        quantity_unit="serving",
    )


def test_shared_proposal_keeps_fixed_dish_serving_per_person() -> None:
    ana = _person(ANA_ID, "Ana")
    rui = _person(RUI_ID, "Rui")

    proposals = _candidate_proposals(
        [_candidate()],
        [
            (ana, _state(ANA_ID, "1800.00", "2000.00")),
            (rui, _state(RUI_ID, "2200.00", "2400.00")),
        ],
        meal_type="lunch",
        auto_size_portions=True,
    )

    assert len(proposals) == 1
    portions = {portion.person_id: portion for portion in proposals[0].portions}
    assert portions[ANA_ID].quantity == Decimal("1.0000")
    assert portions[RUI_ID].quantity == Decimal("1.0000")
    assert portions[ANA_ID].meal_energy_target_min_kcal == Decimal("840.00")
    assert portions[ANA_ID].meal_energy_target_max_kcal == Decimal("933.33")
    assert portions[ANA_ID].energy_allocation_policy == "meal-energy-allocation-v2"
