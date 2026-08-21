from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.daily_nutrition_state import DailyNutritionState
from app.models.family import Family
from app.models.meal import MealEvent, MealParticipant, Serving, ServingNutritionComponent
from app.models.nutrition_target import NutritionTarget, NutritionTargetComponent
from app.models.person import Person
from app.services.daily_nutrition_state import (
    DailyNutritionStateRecalculationError,
    recalculate_daily_nutrition_state,
)


def _person_and_target(db_session: Session) -> tuple[Family, Person, NutritionTarget]:
    family = Family(name="Daily State Test Family", timezone="Europe/Lisbon")
    person = Person(
        family=family,
        first_name="Daily",
        last_name="Tester",
        birth_date=date(1990, 1, 1),
        preferred_locale="pt-PT",
        timezone="Europe/Lisbon",
    )
    target = NutritionTarget(
        person=person,
        valid_from=date(2026, 8, 1),
        valid_until=date(2026, 8, 31),
        energy_min_kcal=Decimal("1800.00"),
        energy_max_kcal=Decimal("2000.00"),
        calculation_version="nutrition-target-v1",
        status="active",
        source="test",
        components=[
            NutritionTargetComponent(
                target_type="nutrient",
                target_key="protein",
                value_min=Decimal("100.0000"),
                value_max=Decimal("140.0000"),
                unit="g",
            ),
            NutritionTargetComponent(
                target_type="nutrient",
                target_key="sodium",
                value_max=Decimal("2000.0000"),
                unit="mg",
            ),
        ],
    )
    db_session.add(family)
    db_session.flush()
    return family, person, target


def _serving(
    *,
    family: Family,
    person: Person,
    scheduled_at: datetime,
    status: str,
    energy_planned: str | None = None,
    energy_served: str | None = None,
    energy_consumed: str | None = None,
    participant_status: str = "planned",
    event_status: str = "planned",
    protein_planned: str | None = None,
    protein_served: str | None = None,
    protein_consumed: str | None = None,
    protein_unit: str = "g",
    sodium_planned: str | None = None,
    sodium_consumed: str | None = None,
    sodium_unit: str = "mg",
) -> Serving:
    event = MealEvent(
        family=family,
        meal_type="meal",
        scheduled_at=scheduled_at,
        timezone="Europe/Lisbon",
        status=event_status,
    )
    participant = MealParticipant(
        meal_event=event,
        person=person,
        status=participant_status,
    )
    components: list[ServingNutritionComponent] = []
    if protein_planned is not None or protein_served is not None or protein_consumed is not None:
        components.append(
            ServingNutritionComponent(
                nutrient_key="protein",
                planned_value=(Decimal(protein_planned) if protein_planned is not None else None),
                served_value=(Decimal(protein_served) if protein_served is not None else None),
                consumed_value=(
                    Decimal(protein_consumed) if protein_consumed is not None else None
                ),
                unit=protein_unit,
            )
        )
    if sodium_planned is not None or sodium_consumed is not None:
        components.append(
            ServingNutritionComponent(
                nutrient_key="sodium",
                planned_value=(Decimal(sodium_planned) if sodium_planned is not None else None),
                consumed_value=(Decimal(sodium_consumed) if sodium_consumed is not None else None),
                unit=sodium_unit,
            )
        )

    serving = Serving(
        meal_participant=participant,
        item_type="dish",
        item_name=f"{status} meal",
        status=status,
        energy_planned_kcal=(Decimal(energy_planned) if energy_planned is not None else None),
        energy_served_kcal=(Decimal(energy_served) if energy_served is not None else None),
        energy_consumed_kcal=(
            Decimal(energy_consumed) if energy_consumed is not None else None
        ),
        nutrition_components=components,
    )
    return serving


def test_recalculation_aggregates_authoritative_servings_and_target_remaining(
    db_session: Session,
) -> None:
    family, person, target = _person_and_target(db_session)
    consumed = _serving(
        family=family,
        person=person,
        scheduled_at=datetime(2026, 8, 22, 7, 0, tzinfo=UTC),
        status="consumed",
        energy_planned="450.00",
        energy_consumed="400.00",
        protein_planned="30.0000",
        protein_consumed="25.0000",
        sodium_planned="0.7000",
        sodium_consumed="0.5000",
        sodium_unit="g",
    )
    planned = _serving(
        family=family,
        person=person,
        scheduled_at=datetime(2026, 8, 22, 18, 0, tzinfo=UTC),
        status="planned",
        energy_planned="600.00",
        protein_planned="40.0000",
        sodium_planned="0.8000",
        sodium_unit="g",
    )
    skipped = _serving(
        family=family,
        person=person,
        scheduled_at=datetime(2026, 8, 22, 12, 0, tzinfo=UTC),
        status="skipped",
        energy_planned="500.00",
        protein_planned="35.0000",
    )
    db_session.add_all([consumed.meal_participant.meal_event, planned.meal_participant.meal_event])
    db_session.add(skipped.meal_participant.meal_event)
    db_session.flush()

    state = recalculate_daily_nutrition_state(
        db_session,
        person=person,
        state_date=date(2026, 8, 22),
        timezone="Europe/Lisbon",
        nutrition_target=target,
    )
    db_session.flush()

    assert state.energy_consumed_kcal == Decimal("400.00")
    assert state.energy_planned_kcal == Decimal("600.00")
    assert state.energy_remaining_min_kcal == Decimal("800.00")
    assert state.energy_remaining_max_kcal == Decimal("1000.00")
    assert state.calculation_inputs is not None
    assert state.calculation_inputs["serving_count"] == 2

    components = {component.target_key: component for component in state.components}
    assert components["protein"].consumed_value == Decimal("25.0000")
    assert components["protein"].planned_value == Decimal("40.0000")
    assert components["protein"].remaining_min == Decimal("35.0000")
    assert components["protein"].remaining_max == Decimal("75.0000")
    assert components["sodium"].consumed_value == Decimal("500.0000")
    assert components["sodium"].planned_value == Decimal("800.0000")
    assert components["sodium"].remaining_max == Decimal("700.0000")


def test_recalculation_uses_local_day_and_served_values(db_session: Session) -> None:
    family, person, target = _person_and_target(db_session)
    target.components.append(
        NutritionTargetComponent(
            target_type="nutrient",
            target_key="fibre",
            value_target=Decimal("30.0000"),
            unit="g",
        )
    )

    included = _serving(
        family=family,
        person=person,
        scheduled_at=datetime(2026, 8, 21, 23, 30, tzinfo=UTC),
        status="served",
        energy_planned="500.00",
        energy_served="450.00",
        protein_planned="30.0000",
        protein_served="28.0000",
    )
    excluded_next_day = _serving(
        family=family,
        person=person,
        scheduled_at=datetime(2026, 8, 22, 23, 30, tzinfo=UTC),
        status="planned",
        energy_planned="900.00",
        protein_planned="60.0000",
    )
    db_session.add_all(
        [included.meal_participant.meal_event, excluded_next_day.meal_participant.meal_event]
    )
    db_session.flush()

    state = recalculate_daily_nutrition_state(
        db_session,
        person=person,
        state_date=date(2026, 8, 22),
        timezone="Europe/Lisbon",
        nutrition_target=target,
    )
    db_session.flush()

    assert state.energy_consumed_kcal == Decimal("0.00")
    assert state.energy_planned_kcal == Decimal("450.00")
    components = {component.target_key: component for component in state.components}
    assert components["protein"].planned_value == Decimal("28.0000")
    assert components["fibre"].consumed_value == Decimal("0.0000")
    assert components["fibre"].planned_value == Decimal("0.0000")
    assert components["fibre"].remaining_min == Decimal("30.0000")
    assert components["fibre"].remaining_max == Decimal("30.0000")


def test_same_calculation_version_recomputes_in_place(db_session: Session) -> None:
    family, person, target = _person_and_target(db_session)
    serving = _serving(
        family=family,
        person=person,
        scheduled_at=datetime(2026, 8, 22, 18, 0, tzinfo=UTC),
        status="planned",
        energy_planned="500.00",
        protein_planned="40.0000",
    )
    db_session.add(serving.meal_participant.meal_event)
    db_session.flush()

    first = recalculate_daily_nutrition_state(
        db_session,
        person=person,
        state_date=date(2026, 8, 22),
        timezone="Europe/Lisbon",
        nutrition_target=target,
    )
    db_session.flush()
    first_id = first.id

    serving.status = "consumed"
    serving.energy_consumed_kcal = Decimal("450.00")
    serving.nutrition_components[0].consumed_value = Decimal("35.0000")

    recalculated = recalculate_daily_nutrition_state(
        db_session,
        person=person,
        state_date=date(2026, 8, 22),
        timezone="Europe/Lisbon",
        nutrition_target=target,
    )
    db_session.flush()

    assert recalculated.id == first_id
    assert recalculated.energy_consumed_kcal == Decimal("450.00")
    assert recalculated.energy_planned_kcal == Decimal("0.00")
    assert recalculated.components[0].consumed_value == Decimal("35.0000")
    assert recalculated.components[0].planned_value == Decimal("0.0000")

    second_version = recalculate_daily_nutrition_state(
        db_session,
        person=person,
        state_date=date(2026, 8, 22),
        timezone="Europe/Lisbon",
        nutrition_target=target,
        calculation_version="daily-nutrition-from-servings-v2",
    )
    db_session.flush()

    assert second_version.id != first_id
    states = list(
        db_session.scalars(
            select(DailyNutritionState).where(
                DailyNutritionState.person_id == person.id,
                DailyNutritionState.state_date == date(2026, 8, 22),
            )
        ).all()
    )
    assert len(states) == 2


def test_recalculation_rejects_unsafe_nutrient_unit_conversion(db_session: Session) -> None:
    family, person, target = _person_and_target(db_session)
    serving = _serving(
        family=family,
        person=person,
        scheduled_at=datetime(2026, 8, 22, 18, 0, tzinfo=UTC),
        status="planned",
        energy_planned="500.00",
        protein_planned="40.0000",
        protein_unit="ml",
    )
    db_session.add(serving.meal_participant.meal_event)
    db_session.flush()

    with pytest.raises(DailyNutritionStateRecalculationError, match="Cannot safely aggregate"):
        recalculate_daily_nutrition_state(
            db_session,
            person=person,
            state_date=date(2026, 8, 22),
            timezone="Europe/Lisbon",
            nutrition_target=target,
        )
