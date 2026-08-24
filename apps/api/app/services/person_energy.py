from datetime import UTC, date, datetime
from decimal import ROUND_HALF_UP, Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.anthropometric_measurement import AnthropometricMeasurement
from app.models.nutrition_goal import NutritionGoal
from app.models.nutrition_target import NutritionTarget
from app.models.person import Person
from app.models.person_profile import PersonProfile
from app.schemas.person import PersonEnergyProfileCreate, PersonEnergyProfileRead

CALCULATION_VERSION = "mifflin-st-jeor-v1"
KCAL_PER_KG = Decimal(7700)
DAYS_PER_WEEK = Decimal(7)
TARGET_HALF_WIDTH_KCAL = Decimal(100)
MAX_GOAL_ADJUSTMENT_FRACTION = Decimal("0.20")
ACTIVITY_FACTORS = {
    "sedentary": Decimal("1.20"),
    "light": Decimal("1.375"),
    "moderate": Decimal("1.55"),
    "active": Decimal("1.725"),
    "very_active": Decimal("1.90"),
}


class PersonEnergyProfileError(ValueError):
    pass


def _q(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _age_years(birth_date: date, on_date: date) -> int:
    years = on_date.year - birth_date.year
    if (on_date.month, on_date.day) < (birth_date.month, birth_date.day):
        years -= 1
    return years


def _mifflin_bmr(
    *,
    sex: str,
    weight_kg: Decimal,
    height_cm: Decimal,
    age_years: int,
) -> Decimal:
    if age_years < 18:
        raise PersonEnergyProfileError(
            "Automatic calorie targets currently require an adult Person (18+)."
        )
    constant = Decimal(5) if sex == "male" else Decimal(-161)
    return _q(
        Decimal(10) * weight_kg
        + Decimal("6.25") * height_cm
        - Decimal(5) * Decimal(age_years)
        + constant
    )


def _goal_adjustment(
    *,
    goal_type: str,
    target_rate_kg_per_week: Decimal | None,
    tdee: Decimal,
) -> Decimal:
    if goal_type == "maintain":
        return Decimal(0)
    if target_rate_kg_per_week is None:
        raise PersonEnergyProfileError("A target rate is required for lose or gain goals.")
    requested = KCAL_PER_KG * target_rate_kg_per_week / DAYS_PER_WEEK
    capped = min(requested, tdee * MAX_GOAL_ADJUSTMENT_FRACTION)
    return -capped if goal_type == "lose" else capped


def _ensure_profile(person: Person) -> PersonProfile:
    if person.profile is None:
        person.profile = PersonProfile(
            measurement_system="metric",
            energy_unit="kcal",
        )
    return person.profile


def _supersede_active_energy_records(
    session: Session,
    *,
    person: Person,
    local_date: date,
) -> None:
    goals = session.scalars(
        select(NutritionGoal).where(
            NutritionGoal.person_id == person.id,
            NutritionGoal.status == "active",
        )
    ).all()
    for goal in goals:
        goal.status = "superseded"

    targets = session.scalars(
        select(NutritionTarget).where(
            NutritionTarget.person_id == person.id,
            NutritionTarget.status == "active",
        )
    ).all()
    for target in targets:
        target.status = "superseded"
        if target.valid_until is None and local_date >= target.valid_from:
            target.valid_until = local_date


def _apply_energy_profile(
    session: Session,
    *,
    person: Person,
    data: PersonEnergyProfileCreate,
    now: datetime | None,
    supersede_existing: bool,
) -> NutritionTarget:
    if person.birth_date is None:
        raise PersonEnergyProfileError("birth_date is required for calorie target calculation.")
    instant = now or datetime.now(UTC)
    local_date = instant.astimezone(ZoneInfo(person.timezone)).date()
    age_years = _age_years(person.birth_date, local_date)
    bmr = _mifflin_bmr(
        sex=data.sex_for_energy_calculation,
        weight_kg=data.weight_kg,
        height_cm=data.height_cm,
        age_years=age_years,
    )
    factor = ACTIVITY_FACTORS[data.activity_level]
    tdee = _q(bmr * factor)
    adjustment = _goal_adjustment(
        goal_type=data.goal_type,
        target_rate_kg_per_week=data.target_rate_kg_per_week,
        tdee=tdee,
    )
    center = _q(tdee + adjustment)
    energy_min = _q(max(Decimal(1), center - TARGET_HALF_WIDTH_KCAL))
    energy_max = _q(center + TARGET_HALF_WIDTH_KCAL)

    if supersede_existing:
        _supersede_active_energy_records(
            session,
            person=person,
            local_date=local_date,
        )

    profile = _ensure_profile(person)
    profile.sex_for_energy_calculation = data.sex_for_energy_calculation
    profile.activity_level = data.activity_level
    profile.standard_breakfast_kcal = data.standard_breakfast_kcal
    profile.measurement_system = "metric"
    profile.energy_unit = "kcal"

    session.add_all(
        [
            AnthropometricMeasurement(
                person=person,
                metric="height",
                value=data.height_cm,
                unit="cm",
                measured_at=instant,
                source="manual",
            ),
            AnthropometricMeasurement(
                person=person,
                metric="weight",
                value=data.weight_kg,
                unit="kg",
                measured_at=instant,
                source="manual",
            ),
        ]
    )
    goal = NutritionGoal(
        person=person,
        goal_type=data.goal_type,
        target_rate_kg_per_week=(
            None if data.goal_type == "maintain" else data.target_rate_kg_per_week
        ),
        start_date=local_date,
        status="active",
        source="user",
    )
    session.add(goal)
    session.flush()
    target = NutritionTarget(
        person=person,
        nutrition_goal_id=goal.id,
        valid_from=local_date,
        estimated_bmr_kcal=bmr,
        bmr_method="Mifflin-St Jeor",
        estimated_tdee_kcal=tdee,
        tdee_method=f"Mifflin-St Jeor x {data.activity_level}",
        energy_min_kcal=energy_min,
        energy_max_kcal=energy_max,
        calculation_version=CALCULATION_VERSION,
        calculation_inputs={
            "age_years": age_years,
            "sex_for_energy_calculation": data.sex_for_energy_calculation,
            "height_cm": str(data.height_cm),
            "weight_kg": str(data.weight_kg),
            "activity_level": data.activity_level,
            "activity_factor": str(factor),
            "goal_type": data.goal_type,
            "target_rate_kg_per_week": (
                str(data.target_rate_kg_per_week)
                if data.target_rate_kg_per_week is not None
                else None
            ),
            "goal_adjustment_kcal": str(_q(adjustment)),
            "goal_adjustment_cap": "20_percent_tdee",
            "target_half_width_kcal": str(TARGET_HALF_WIDTH_KCAL),
        },
        status="active",
        source="system",
        notes="Automatically estimated from the Person setup profile.",
    )
    session.add(target)
    return target


def create_energy_profile(
    session: Session,
    *,
    person: Person,
    data: PersonEnergyProfileCreate,
    now: datetime | None = None,
) -> NutritionTarget:
    return _apply_energy_profile(
        session,
        person=person,
        data=data,
        now=now,
        supersede_existing=False,
    )


def update_energy_profile(
    session: Session,
    *,
    person: Person,
    data: PersonEnergyProfileCreate,
    now: datetime | None = None,
) -> NutritionTarget:
    return _apply_energy_profile(
        session,
        person=person,
        data=data,
        now=now,
        supersede_existing=True,
    )


def _latest_measurement(session: Session, person_id, metric: str) -> Decimal:
    value = session.scalar(
        select(AnthropometricMeasurement.value)
        .where(
            AnthropometricMeasurement.person_id == person_id,
            AnthropometricMeasurement.metric == metric,
        )
        .order_by(
            AnthropometricMeasurement.measured_at.desc(),
            AnthropometricMeasurement.created_at.desc(),
        )
        .limit(1)
    )
    if value is None:
        raise PersonEnergyProfileError(f"Missing {metric} measurement.")
    return value


def get_energy_profile(session: Session, *, person: Person) -> PersonEnergyProfileRead:
    profile = person.profile
    if (
        profile is None
        or profile.sex_for_energy_calculation is None
        or profile.activity_level is None
        or profile.standard_breakfast_kcal is None
    ):
        raise PersonEnergyProfileError("Person does not have a complete energy profile.")
    goal = session.scalar(
        select(NutritionGoal)
        .where(NutritionGoal.person_id == person.id, NutritionGoal.status == "active")
        .order_by(NutritionGoal.start_date.desc(), NutritionGoal.created_at.desc())
        .limit(1)
    )
    target = session.scalar(
        select(NutritionTarget)
        .where(NutritionTarget.person_id == person.id, NutritionTarget.status == "active")
        .order_by(NutritionTarget.valid_from.desc(), NutritionTarget.created_at.desc())
        .limit(1)
    )
    if goal is None or target is None:
        raise PersonEnergyProfileError("Person does not have an active calorie target.")
    required = (
        target.estimated_bmr_kcal,
        target.estimated_tdee_kcal,
        target.energy_min_kcal,
        target.energy_max_kcal,
    )
    if any(value is None for value in required):
        raise PersonEnergyProfileError("Person calorie target is incomplete.")

    return PersonEnergyProfileRead(
        person_id=person.id,
        sex_for_energy_calculation=profile.sex_for_energy_calculation,
        activity_level=profile.activity_level,
        standard_breakfast_kcal=profile.standard_breakfast_kcal,
        height_cm=_latest_measurement(session, person.id, "height"),
        weight_kg=_latest_measurement(session, person.id, "weight"),
        goal_type=goal.goal_type,
        target_rate_kg_per_week=goal.target_rate_kg_per_week,
        estimated_bmr_kcal=target.estimated_bmr_kcal,
        estimated_tdee_kcal=target.estimated_tdee_kcal,
        energy_min_kcal=target.energy_min_kcal,
        energy_max_kcal=target.energy_max_kcal,
        calculation_version=target.calculation_version,
    )
