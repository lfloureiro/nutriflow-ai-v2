import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.daily_nutrition_state import DailyNutritionState, DailyNutritionStateComponent
from app.models.family import Family
from app.models.food_catalog import FoodCompositionSnapshot, FoodItem, FoodNutrientComponent
from app.models.food_preference import FoodPreference
from app.models.nutrition_constraint import NutritionConstraint
from app.models.person import Person

DEMO_TIMEZONE = "Europe/Lisbon"
DEMO_FAMILY_ID = uuid.UUID("11111111-1111-4111-8111-111111111111")
DEMO_PERSON_ID = uuid.UUID("22222222-2222-4222-8222-222222222222")
DEMO_PREFERENCE_ID = uuid.UUID("88888888-8888-4888-8888-888888888881")
DEMO_SODIUM_CONSTRAINT_ID = uuid.UUID("88888888-8888-4888-8888-888888888882")
DEMO_CALCULATION_VERSION = "demo-seed-v1"
DEMO_DATA_VERSION = "demo-v1"
DEMO_NAMESPACE = uuid.UUID("9e72837a-5324-4f9a-a42e-ec51df9da781")


class DemoSeedConflictError(ValueError):
    pass


@dataclass(frozen=True)
class DemoFoodDefinition:
    id: uuid.UUID
    catalog_key: str
    name: str
    reference_quantity: Decimal
    energy_kcal: Decimal
    protein_g: Decimal
    fiber_g: Decimal
    sodium_mg: Decimal


@dataclass(frozen=True)
class DemoSeedResult:
    family_id: uuid.UUID
    person_id: uuid.UUID
    daily_nutrition_state_id: uuid.UUID
    planning_date: date
    candidate_count: int


DEMO_FOODS = (
    DemoFoodDefinition(
        id=uuid.UUID("33333333-3333-4333-8333-333333333331"),
        catalog_key="demo:massa-bolonhesa",
        name="Massa à bolonhesa",
        reference_quantity=Decimal("400.0000"),
        energy_kcal=Decimal("650.0000"),
        protein_g=Decimal("34.0000"),
        fiber_g=Decimal("7.0000"),
        sodium_mg=Decimal("760.0000"),
    ),
    DemoFoodDefinition(
        id=uuid.UUID("33333333-3333-4333-8333-333333333332"),
        catalog_key="demo:frango-arroz-legumes",
        name="Frango com arroz e legumes",
        reference_quantity=Decimal("420.0000"),
        energy_kcal=Decimal("590.0000"),
        protein_g=Decimal("46.0000"),
        fiber_g=Decimal("8.0000"),
        sodium_mg=Decimal("540.0000"),
    ),
    DemoFoodDefinition(
        id=uuid.UUID("33333333-3333-4333-8333-333333333333"),
        catalog_key="demo:salmao-batata-salada",
        name="Salmão com batata e salada",
        reference_quantity=Decimal("400.0000"),
        energy_kcal=Decimal("560.0000"),
        protein_g=Decimal("38.0000"),
        fiber_g=Decimal("7.0000"),
        sodium_mg=Decimal("480.0000"),
    ),
    DemoFoodDefinition(
        id=uuid.UUID("33333333-3333-4333-8333-333333333334"),
        catalog_key="demo:vaca-ostras-arroz",
        name="Vaca com molho de ostras e arroz",
        reference_quantity=Decimal("450.0000"),
        energy_kcal=Decimal("720.0000"),
        protein_g=Decimal("42.0000"),
        fiber_g=Decimal("5.0000"),
        sodium_mg=Decimal("1250.0000"),
    ),
    DemoFoodDefinition(
        id=uuid.UUID("33333333-3333-4333-8333-333333333335"),
        catalog_key="demo:salada-grao-atum-ovo",
        name="Salada de grão, atum e ovo",
        reference_quantity=Decimal("380.0000"),
        energy_kcal=Decimal("520.0000"),
        protein_g=Decimal("33.0000"),
        fiber_g=Decimal("11.0000"),
        sodium_mg=Decimal("650.0000"),
    ),
    DemoFoodDefinition(
        id=uuid.UUID("33333333-3333-4333-8333-333333333336"),
        catalog_key="demo:pizza-pepperoni",
        name="Pizza pepperoni",
        reference_quantity=Decimal("380.0000"),
        energy_kcal=Decimal("880.0000"),
        protein_g=Decimal("36.0000"),
        fiber_g=Decimal("5.0000"),
        sodium_mg=Decimal("1650.0000"),
    ),
)


def _state_id(state_date: date) -> uuid.UUID:
    return uuid.uuid5(DEMO_NAMESPACE, f"daily-state:{state_date.isoformat()}")


def _component_id(state_date: date, key: str) -> uuid.UUID:
    return uuid.uuid5(DEMO_NAMESPACE, f"daily-state:{state_date.isoformat()}:{key}")


def _snapshot_id(food_id: uuid.UUID) -> uuid.UUID:
    return uuid.uuid5(DEMO_NAMESPACE, f"food-snapshot:{food_id}:{DEMO_DATA_VERSION}")


def _nutrient_id(food_id: uuid.UUID, key: str) -> uuid.UUID:
    return uuid.uuid5(DEMO_NAMESPACE, f"food-nutrient:{food_id}:{DEMO_DATA_VERSION}:{key}")


def _ensure_family(session: Session) -> Family:
    family = session.get(Family, DEMO_FAMILY_ID)
    if family is None:
        family = Family(id=DEMO_FAMILY_ID, name="NutriFlow Demo", timezone=DEMO_TIMEZONE)
        session.add(family)
    else:
        family.name = "NutriFlow Demo"
        family.timezone = DEMO_TIMEZONE
    return family


def _ensure_person(session: Session, family: Family) -> Person:
    person = session.get(Person, DEMO_PERSON_ID)
    if person is None:
        person = Person(
            id=DEMO_PERSON_ID,
            family=family,
            first_name="Pessoa",
            last_name="Demo",
            preferred_locale="pt-PT",
            timezone=DEMO_TIMEZONE,
        )
        session.add(person)
    else:
        person.family_id = family.id
        person.first_name = "Pessoa"
        person.last_name = "Demo"
        person.preferred_locale = "pt-PT"
        person.timezone = DEMO_TIMEZONE
    return person


def _ensure_food(session: Session, family: Family, definition: DemoFoodDefinition, now: datetime) -> None:
    key_owner = session.scalar(select(FoodItem).where(FoodItem.catalog_key == definition.catalog_key))
    if key_owner is not None and key_owner.id != definition.id:
        raise DemoSeedConflictError(
            f"Catalogue key {definition.catalog_key!r} already belongs to another FoodItem."
        )

    food = session.get(FoodItem, definition.id)
    if food is None:
        food = FoodItem(
            id=definition.id,
            family=family,
            catalog_key=definition.catalog_key,
            name=definition.name,
            food_kind="dish",
            source="demo",
            source_reference="nutriflow-development-demo",
            is_active=True,
        )
        session.add(food)
    else:
        food.family_id = family.id
        food.catalog_key = definition.catalog_key
        food.name = definition.name
        food.food_kind = "dish"
        food.source = "demo"
        food.source_reference = "nutriflow-development-demo"
        food.is_active = True

    snapshot_id = _snapshot_id(definition.id)
    snapshot = session.get(FoodCompositionSnapshot, snapshot_id)
    if snapshot is None:
        snapshot = FoodCompositionSnapshot(
            id=snapshot_id,
            food_item=food,
            reference_quantity=definition.reference_quantity,
            reference_unit="g",
            energy_kcal=definition.energy_kcal,
            data_version=DEMO_DATA_VERSION,
            source="demo",
            source_reference="nutriflow-development-demo",
            effective_at=now,
            notes="Synthetic development-only nutrition data.",
        )
        session.add(snapshot)
    else:
        snapshot.food_item_id = food.id
        snapshot.reference_quantity = definition.reference_quantity
        snapshot.reference_unit = "g"
        snapshot.energy_kcal = definition.energy_kcal
        snapshot.data_version = DEMO_DATA_VERSION
        snapshot.source = "demo"
        snapshot.source_reference = "nutriflow-development-demo"
        snapshot.notes = "Synthetic development-only nutrition data."
        if snapshot.effective_at > now:
            snapshot.effective_at = now

    nutrients = {
        "protein": (definition.protein_g, "g"),
        "fiber": (definition.fiber_g, "g"),
        "sodium": (definition.sodium_mg, "mg"),
    }
    for nutrient_key, (value, unit) in nutrients.items():
        nutrient_id = _nutrient_id(definition.id, nutrient_key)
        nutrient = session.get(FoodNutrientComponent, nutrient_id)
        if nutrient is None:
            nutrient = FoodNutrientComponent(
                id=nutrient_id,
                composition_snapshot=snapshot,
                nutrient_key=nutrient_key,
                value=value,
                unit=unit,
            )
            session.add(nutrient)
        else:
            nutrient.composition_snapshot_id = snapshot.id
            nutrient.nutrient_key = nutrient_key
            nutrient.value = value
            nutrient.unit = unit


def _ensure_daily_state(session: Session, person: Person, now: datetime) -> DailyNutritionState:
    local_date = now.astimezone(ZoneInfo(DEMO_TIMEZONE)).date()
    state_id = _state_id(local_date)
    state = session.get(DailyNutritionState, state_id)
    if state is None:
        state = DailyNutritionState(
            id=state_id,
            person=person,
            state_date=local_date,
            timezone=DEMO_TIMEZONE,
            energy_consumed_kcal=Decimal("1000.00"),
            energy_planned_kcal=Decimal("0.00"),
            energy_remaining_min_kcal=Decimal("500.00"),
            energy_remaining_max_kcal=Decimal("900.00"),
            adherence_score=Decimal("0.8000"),
            confidence_score=Decimal("1.0000"),
            calculation_version=DEMO_CALCULATION_VERSION,
            calculation_inputs={"source": "development-demo-seed"},
            computed_at=now,
        )
        session.add(state)
    else:
        state.person_id = person.id
        state.state_date = local_date
        state.timezone = DEMO_TIMEZONE
        state.energy_consumed_kcal = Decimal("1000.00")
        state.energy_planned_kcal = Decimal("0.00")
        state.energy_remaining_min_kcal = Decimal("500.00")
        state.energy_remaining_max_kcal = Decimal("900.00")
        state.adherence_score = Decimal("0.8000")
        state.confidence_score = Decimal("1.0000")
        state.calculation_version = DEMO_CALCULATION_VERSION
        state.calculation_inputs = {"source": "development-demo-seed"}
        state.computed_at = now

    component_values = {
        "protein": (Decimal("45.0000"), Decimal("35.0000"), Decimal("80.0000"), "g"),
        "fiber": (Decimal("12.0000"), Decimal("12.0000"), Decimal("28.0000"), "g"),
        "sodium": (Decimal("1000.0000"), None, Decimal("1300.0000"), "mg"),
    }
    for key, (consumed, remaining_min, remaining_max, unit) in component_values.items():
        component_id = _component_id(local_date, key)
        component = session.get(DailyNutritionStateComponent, component_id)
        if component is None:
            component = DailyNutritionStateComponent(
                id=component_id,
                daily_nutrition_state=state,
                target_type="nutrient",
                target_key=key,
                consumed_value=consumed,
                planned_value=Decimal("0.0000"),
                remaining_min=remaining_min,
                remaining_max=remaining_max,
                unit=unit,
            )
            session.add(component)
        else:
            component.daily_nutrition_state_id = state.id
            component.target_type = "nutrient"
            component.target_key = key
            component.consumed_value = consumed
            component.planned_value = Decimal("0.0000")
            component.remaining_min = remaining_min
            component.remaining_max = remaining_max
            component.unit = unit
    return state


def _ensure_demo_rules(session: Session, person: Person) -> None:
    preference = session.get(FoodPreference, DEMO_PREFERENCE_ID)
    if preference is None:
        preference = FoodPreference(
            id=DEMO_PREFERENCE_ID,
            person=person,
            subject_type="dish",
            subject_key="demo:massa-bolonhesa",
            preference_type="like",
            intensity=4,
            source="demo",
            notes="Development-only ranking signal.",
        )
        session.add(preference)
    else:
        preference.person_id = person.id
        preference.subject_type = "dish"
        preference.subject_key = "demo:massa-bolonhesa"
        preference.preference_type = "like"
        preference.intensity = 4
        preference.source = "demo"
        preference.notes = "Development-only ranking signal."

    constraint = session.get(NutritionConstraint, DEMO_SODIUM_CONSTRAINT_ID)
    if constraint is None:
        constraint = NutritionConstraint(
            id=DEMO_SODIUM_CONSTRAINT_ID,
            person=person,
            constraint_type="daily_limit",
            target_type="nutrient",
            target_key="sodium",
            operator="max",
            value_max=Decimal("2300.0000"),
            unit="mg",
            severity="mandatory",
            is_mandatory=True,
            source="demo",
            source_name="NutriFlow development demo",
            notes="Synthetic development-only mandatory maximum.",
        )
        session.add(constraint)
    else:
        constraint.person_id = person.id
        constraint.constraint_type = "daily_limit"
        constraint.target_type = "nutrient"
        constraint.target_key = "sodium"
        constraint.operator = "max"
        constraint.value_min = None
        constraint.value_max = Decimal("2300.0000")
        constraint.unit = "mg"
        constraint.severity = "mandatory"
        constraint.is_mandatory = True
        constraint.source = "demo"
        constraint.source_name = "NutriFlow development demo"
        constraint.notes = "Synthetic development-only mandatory maximum."


def seed_demo_dataset(session: Session, *, now: datetime | None = None) -> DemoSeedResult:
    instant = now or datetime.now(UTC)
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise ValueError("Demo seed instant must be timezone-aware.")
    instant = instant.astimezone(UTC)

    family = _ensure_family(session)
    person = _ensure_person(session, family)
    session.flush()

    for definition in DEMO_FOODS:
        _ensure_food(session, family, definition, instant)
    state = _ensure_daily_state(session, person, instant)
    _ensure_demo_rules(session, person)
    session.flush()

    return DemoSeedResult(
        family_id=family.id,
        person_id=person.id,
        daily_nutrition_state_id=state.id,
        planning_date=state.state_date,
        candidate_count=len(DEMO_FOODS),
    )


def main() -> None:
    with SessionLocal() as session:
        result = seed_demo_dataset(session)
        session.commit()

    print("NutriFlow development demo dataset ready.")
    print(f"Family ID: {result.family_id}")
    print(f"Person ID: {result.person_id}")
    print(f"Planning date: {result.planning_date.isoformat()}")
    print(f"Candidates: {result.candidate_count}")


if __name__ == "__main__":
    main()
