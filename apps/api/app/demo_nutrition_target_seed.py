import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.demo_seed import (
    DEMO_FAMILY_ID,
    DEMO_INES_ID,
    DEMO_MARTA_ID,
    DEMO_NAMESPACE,
    DEMO_PERSON_ID,
    DEMO_RUI_ID,
    DEMO_TIMEZONE,
)
from app.models.daily_nutrition_state import DailyNutritionState
from app.models.nutrition_target import NutritionTarget, NutritionTargetComponent
from app.models.person import Person

DEMO_TARGET_CALCULATION_VERSION = "demo-nutrition-target-v1"
DEMO_BUDGET_CALCULATION_VERSION = "demo-energy-budget-v1"
DEMO_TARGET_VALID_FROM = date(2026, 1, 1)


@dataclass(frozen=True)
class DemoNutritionTargetDefinition:
    person_id: uuid.UUID
    estimated_bmr_kcal: Decimal
    estimated_tdee_kcal: Decimal
    energy_min_kcal: Decimal
    energy_max_kcal: Decimal
    current_consumed_kcal: Decimal
    current_planned_kcal: Decimal
    protein_min_g: Decimal
    protein_max_g: Decimal
    fiber_min_g: Decimal
    sodium_max_mg: Decimal


@dataclass(frozen=True)
class DemoNutritionTargetSeedResult:
    target_count: int
    state_count: int


DEMO_NUTRITION_TARGETS = (
    DemoNutritionTargetDefinition(
        person_id=DEMO_PERSON_ID,
        estimated_bmr_kcal=Decimal(1850),
        estimated_tdee_kcal=Decimal(2220),
        energy_min_kcal=Decimal(1800),
        energy_max_kcal=Decimal(2000),
        current_consumed_kcal=Decimal(1000),
        current_planned_kcal=Decimal(0),
        protein_min_g=Decimal(110),
        protein_max_g=Decimal(140),
        fiber_min_g=Decimal(25),
        sodium_max_mg=Decimal(2300),
    ),
    DemoNutritionTargetDefinition(
        person_id=DEMO_MARTA_ID,
        estimated_bmr_kcal=Decimal(1380),
        estimated_tdee_kcal=Decimal(1800),
        energy_min_kcal=Decimal(1700),
        energy_max_kcal=Decimal(1900),
        current_consumed_kcal=Decimal(850),
        current_planned_kcal=Decimal(450),
        protein_min_g=Decimal(80),
        protein_max_g=Decimal(110),
        fiber_min_g=Decimal(25),
        sodium_max_mg=Decimal(2300),
    ),
    DemoNutritionTargetDefinition(
        person_id=DEMO_RUI_ID,
        estimated_bmr_kcal=Decimal(1750),
        estimated_tdee_kcal=Decimal(2400),
        energy_min_kcal=Decimal(2200),
        energy_max_kcal=Decimal(2400),
        current_consumed_kcal=Decimal(1200),
        current_planned_kcal=Decimal(600),
        protein_min_g=Decimal(120),
        protein_max_g=Decimal(150),
        fiber_min_g=Decimal(30),
        sodium_max_mg=Decimal(2300),
    ),
    DemoNutritionTargetDefinition(
        person_id=DEMO_INES_ID,
        estimated_bmr_kcal=Decimal(1320),
        estimated_tdee_kcal=Decimal(1750),
        energy_min_kcal=Decimal(1600),
        energy_max_kcal=Decimal(1800),
        current_consumed_kcal=Decimal(700),
        current_planned_kcal=Decimal(0),
        protein_min_g=Decimal(75),
        protein_max_g=Decimal(100),
        fiber_min_g=Decimal(25),
        sodium_max_mg=Decimal(2300),
    ),
)


def _target_id(person_id: uuid.UUID) -> uuid.UUID:
    return uuid.uuid5(DEMO_NAMESPACE, f"nutrition-target:{person_id}:{DEMO_TARGET_CALCULATION_VERSION}")


def _component_id(person_id: uuid.UUID, key: str) -> uuid.UUID:
    return uuid.uuid5(
        DEMO_NAMESPACE,
        f"nutrition-target-component:{person_id}:{DEMO_TARGET_CALCULATION_VERSION}:{key}",
    )


def _state_id(person_id: uuid.UUID, state_date: date) -> uuid.UUID:
    return uuid.uuid5(DEMO_NAMESPACE, f"demo-energy-state:{person_id}:{state_date.isoformat()}")


def _ensure_target_component(
    session: Session,
    *,
    target: NutritionTarget,
    person_id: uuid.UUID,
    key: str,
    value_min: Decimal | None,
    value_max: Decimal | None,
    unit: str,
) -> None:
    component_id = _component_id(person_id, key)
    component = session.get(NutritionTargetComponent, component_id)
    if component is None:
        component = NutritionTargetComponent(
            id=component_id,
            nutrition_target=target,
            target_type="nutrient",
            target_key=key,
            unit=unit,
        )
        session.add(component)
    component.nutrition_target_id = target.id
    component.target_type = "nutrient"
    component.target_key = key
    component.value_min = value_min
    component.value_max = value_max
    component.value_target = None
    component.unit = unit


def _ensure_target(
    session: Session,
    *,
    person: Person,
    definition: DemoNutritionTargetDefinition,
) -> NutritionTarget:
    target_id = _target_id(person.id)
    target = session.get(NutritionTarget, target_id)
    if target is None:
        target = NutritionTarget(
            id=target_id,
            person=person,
            valid_from=DEMO_TARGET_VALID_FROM,
            calculation_version=DEMO_TARGET_CALCULATION_VERSION,
        )
        session.add(target)

    target.person_id = person.id
    target.valid_from = DEMO_TARGET_VALID_FROM
    target.valid_until = None
    target.estimated_bmr_kcal = definition.estimated_bmr_kcal
    target.bmr_method = "synthetic-development-demo"
    target.estimated_tdee_kcal = definition.estimated_tdee_kcal
    target.tdee_method = "synthetic-development-demo"
    target.energy_min_kcal = definition.energy_min_kcal
    target.energy_max_kcal = definition.energy_max_kcal
    target.calculation_version = DEMO_TARGET_CALCULATION_VERSION
    target.calculation_inputs = {
        "source": "synthetic-development-demo",
        "purpose": "exercise calorie-aware recommendation and planning flows",
    }
    target.status = "active"
    target.source = "demo"
    target.notes = "Synthetic development-only calorie and nutrient target."
    session.flush()

    _ensure_target_component(
        session,
        target=target,
        person_id=person.id,
        key="protein",
        value_min=definition.protein_min_g,
        value_max=definition.protein_max_g,
        unit="g",
    )
    _ensure_target_component(
        session,
        target=target,
        person_id=person.id,
        key="fiber",
        value_min=definition.fiber_min_g,
        value_max=None,
        unit="g",
    )
    _ensure_target_component(
        session,
        target=target,
        person_id=person.id,
        key="sodium",
        value_min=None,
        value_max=definition.sodium_max_mg,
        unit="mg",
    )
    return target


def _latest_state(
    session: Session,
    *,
    person_id: uuid.UUID,
    state_date: date,
) -> DailyNutritionState | None:
    return session.scalar(
        select(DailyNutritionState)
        .where(
            DailyNutritionState.person_id == person_id,
            DailyNutritionState.state_date == state_date,
        )
        .options(selectinload(DailyNutritionState.components))
        .order_by(
            DailyNutritionState.computed_at.desc(),
            DailyNutritionState.created_at.desc(),
            DailyNutritionState.id.desc(),
        )
        .limit(1)
    )


def _ensure_current_budget_state(
    session: Session,
    *,
    person: Person,
    target: NutritionTarget,
    definition: DemoNutritionTargetDefinition,
    state_date: date,
    now: datetime,
) -> DailyNutritionState:
    state = _latest_state(session, person_id=person.id, state_date=state_date)
    if state is None:
        state = DailyNutritionState(
            id=_state_id(person.id, state_date),
            person=person,
            state_date=state_date,
            timezone=DEMO_TIMEZONE,
            calculation_version=DEMO_BUDGET_CALCULATION_VERSION,
        )
        session.add(state)

    spent = definition.current_consumed_kcal + definition.current_planned_kcal
    state.person_id = person.id
    state.nutrition_target = target
    state.state_date = state_date
    state.timezone = DEMO_TIMEZONE
    state.energy_consumed_kcal = definition.current_consumed_kcal
    state.energy_planned_kcal = definition.current_planned_kcal
    state.energy_remaining_min_kcal = definition.energy_min_kcal - spent
    state.energy_remaining_max_kcal = definition.energy_max_kcal - spent
    state.adherence_score = None
    state.confidence_score = Decimal(1)
    state.calculation_version = DEMO_BUDGET_CALCULATION_VERSION
    state.calculation_inputs = {
        "source": "synthetic-development-demo",
        "nutrition_target_id": str(target.id),
        "purpose": "show consumed, planned and remaining calories in recommendation UI",
    }
    state.computed_at = now
    return state


def seed_demo_nutrition_targets(
    session: Session,
    *,
    now: datetime | None = None,
) -> DemoNutritionTargetSeedResult:
    instant = now or datetime.now(UTC)
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise ValueError("Demo nutrition target seed instant must be timezone-aware.")
    instant = instant.astimezone(UTC)
    local_date = instant.astimezone(ZoneInfo(DEMO_TIMEZONE)).date()

    people = {
        person.id: person
        for person in session.scalars(
            select(Person).where(Person.family_id == DEMO_FAMILY_ID)
        ).all()
    }

    state_count = 0
    for definition in DEMO_NUTRITION_TARGETS:
        person = people.get(definition.person_id)
        if person is None:
            raise RuntimeError(
                f"Development demo Person {definition.person_id} must exist before calorie targets."
            )
        target = _ensure_target(session, person=person, definition=definition)
        _ensure_current_budget_state(
            session,
            person=person,
            target=target,
            definition=definition,
            state_date=local_date,
            now=instant,
        )
        state_count += 1

    session.flush()
    return DemoNutritionTargetSeedResult(
        target_count=len(DEMO_NUTRITION_TARGETS),
        state_count=state_count,
    )
