from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.main import app
from app.models.daily_nutrition_state import DailyNutritionState
from app.models.family import Family
from app.models.food_catalog import (
    FoodCompositionSnapshot,
    FoodItem,
    Recipe,
    RecipeCompositionSnapshot,
)
from app.models.person import Person

SCHEDULED_AT = datetime(2026, 8, 22, 12, 0, tzinfo=UTC)


def _override_db(db_session: Session):
    def override_get_db():
        yield db_session

    return override_get_db


def _get(db_session: Session, person: Person, scheduled_at: datetime | str = SCHEDULED_AT):
    value = scheduled_at if isinstance(scheduled_at, str) else scheduled_at.isoformat()
    app.dependency_overrides[get_db] = _override_db(db_session)
    try:
        with TestClient(app) as client:
            return client.get(
                f"/api/persons/{person.id}/planning-bootstrap",
                params={"scheduled_at": value},
            )
    finally:
        app.dependency_overrides.clear()


def _family_person(
    db_session: Session,
    *,
    key: str,
    timezone: str = "Europe/Lisbon",
) -> tuple[Family, Person]:
    family = Family(name=f"Bootstrap {key}", timezone=timezone)
    person = Person(
        family=family,
        first_name="Ana",
        preferred_locale="pt-PT",
        timezone=timezone,
    )
    db_session.add(family)
    db_session.flush()
    return family, person


def _state(
    person: Person,
    *,
    state_date: date,
    version: str,
    computed_at: datetime,
    remaining_max: str,
) -> DailyNutritionState:
    return DailyNutritionState(
        person=person,
        state_date=state_date,
        timezone=person.timezone,
        energy_consumed_kcal=Decimal("900.00"),
        energy_planned_kcal=Decimal("300.00"),
        energy_remaining_min_kcal=Decimal("200.00"),
        energy_remaining_max_kcal=Decimal(remaining_max),
        calculation_version=version,
        computed_at=computed_at,
    )


def _food_snapshot(
    food: FoodItem,
    *,
    version: str,
    effective_at: datetime,
    energy: str,
) -> FoodCompositionSnapshot:
    return FoodCompositionSnapshot(
        food_item=food,
        reference_quantity=Decimal("100.0000"),
        reference_unit="g",
        energy_kcal=Decimal(energy),
        data_version=version,
        source="test",
        effective_at=effective_at,
    )


def test_bootstrap_uses_person_local_date_and_latest_daily_state(db_session: Session) -> None:
    _, person = _family_person(db_session, key="local-date", timezone="Pacific/Auckland")
    scheduled_at = datetime(2026, 8, 21, 12, 30, tzinfo=UTC)
    local_date = date(2026, 8, 22)
    db_session.add_all(
        [
            _state(
                person,
                state_date=local_date,
                version="older",
                computed_at=scheduled_at - timedelta(hours=2),
                remaining_max="500.00",
            ),
            _state(
                person,
                state_date=local_date,
                version="latest",
                computed_at=scheduled_at - timedelta(minutes=5),
                remaining_max="650.00",
            ),
        ]
    )
    db_session.flush()

    response = _get(db_session, person, scheduled_at)

    assert response.status_code == 200
    body = response.json()
    assert body["planning_date"] == "2026-08-22"
    assert body["daily_nutrition_state"]["calculation_version"] == "latest"
    assert Decimal(body["daily_nutrition_state"]["energy_remaining_max_kcal"]) == Decimal(
        "650.00"
    )


def test_bootstrap_returns_global_and_family_catalogue_only(db_session: Session) -> None:
    family, person = _family_person(db_session, key="scope")
    other_family = Family(name="Other", timezone="Europe/Lisbon")
    family_food = FoodItem(
        family=family,
        catalog_key="food:family",
        name="Family dish",
        food_kind="dish",
        source="test",
    )
    global_food = FoodItem(
        catalog_key="food:global",
        name="Global dish",
        food_kind="dish",
        source="test",
    )
    other_food = FoodItem(
        family=other_family,
        catalog_key="food:other",
        name="Other dish",
        food_kind="dish",
        source="test",
    )
    inactive_food = FoodItem(
        family=family,
        catalog_key="food:inactive",
        name="Inactive dish",
        food_kind="dish",
        source="test",
        is_active=False,
    )
    db_session.add_all(
        [
            other_family,
            _food_snapshot(
                family_food,
                version="v1",
                effective_at=SCHEDULED_AT - timedelta(days=1),
                energy="300.00",
            ),
            _food_snapshot(
                global_food,
                version="v1",
                effective_at=SCHEDULED_AT - timedelta(days=1),
                energy="320.00",
            ),
            _food_snapshot(
                other_food,
                version="v1",
                effective_at=SCHEDULED_AT - timedelta(days=1),
                energy="340.00",
            ),
            _food_snapshot(
                inactive_food,
                version="v1",
                effective_at=SCHEDULED_AT - timedelta(days=1),
                energy="360.00",
            ),
        ]
    )
    db_session.flush()

    response = _get(db_session, person)

    assert response.status_code == 200
    keys = {candidate["catalog_key"] for candidate in response.json()["candidates"]}
    assert keys == {"food:family", "food:global"}


def test_bootstrap_selects_latest_food_snapshot_not_future_data(db_session: Session) -> None:
    family, person = _family_person(db_session, key="food-version")
    food = FoodItem(
        family=family,
        catalog_key="food:versioned",
        name="Versioned dish",
        food_kind="dish",
        source="test",
    )
    old = _food_snapshot(
        food,
        version="v1",
        effective_at=SCHEDULED_AT - timedelta(days=2),
        energy="250.00",
    )
    current = _food_snapshot(
        food,
        version="v2",
        effective_at=SCHEDULED_AT - timedelta(hours=1),
        energy="300.00",
    )
    future = _food_snapshot(
        food,
        version="v3",
        effective_at=SCHEDULED_AT + timedelta(hours=1),
        energy="350.00",
    )
    db_session.add_all([old, current, future])
    db_session.flush()
    assert current.id is not None

    response = _get(db_session, person)

    assert response.status_code == 200
    candidate = response.json()["candidates"][0]
    assert candidate["composition_id"] == str(current.id)
    assert candidate["composition_version"] == "v2"
    assert Decimal(candidate["energy_kcal"]) == Decimal("300.0000")


def test_bootstrap_selects_latest_recipe_snapshot_as_of_schedule(db_session: Session) -> None:
    family, person = _family_person(db_session, key="recipe-version")
    recipe = Recipe(
        family=family,
        recipe_key="recipe:pasta",
        name="Pasta",
        yield_quantity=Decimal("400.0000"),
        yield_unit="g",
        source="test",
    )
    old = RecipeCompositionSnapshot(
        recipe=recipe,
        reference_quantity=Decimal("400.0000"),
        reference_unit="g",
        energy_kcal=Decimal("700.0000"),
        composition_version="v1",
        calculation_version="test",
        computed_at=SCHEDULED_AT - timedelta(days=1),
    )
    current = RecipeCompositionSnapshot(
        recipe=recipe,
        reference_quantity=Decimal("400.0000"),
        reference_unit="g",
        energy_kcal=Decimal("720.0000"),
        composition_version="v2",
        calculation_version="test",
        computed_at=SCHEDULED_AT - timedelta(minutes=30),
    )
    future = RecipeCompositionSnapshot(
        recipe=recipe,
        reference_quantity=Decimal("400.0000"),
        reference_unit="g",
        energy_kcal=Decimal("740.0000"),
        composition_version="v3",
        calculation_version="test",
        computed_at=SCHEDULED_AT + timedelta(minutes=30),
    )
    db_session.add_all([old, current, future])
    db_session.flush()
    assert current.id is not None

    response = _get(db_session, person)

    assert response.status_code == 200
    candidate = response.json()["candidates"][0]
    assert candidate["candidate_kind"] == "recipe"
    assert candidate["composition_id"] == str(current.id)
    assert candidate["composition_version"] == "v2"


def test_bootstrap_returns_null_daily_state_when_not_yet_computed(db_session: Session) -> None:
    _, person = _family_person(db_session, key="no-state")

    response = _get(db_session, person)

    assert response.status_code == 200
    assert response.json()["daily_nutrition_state"] is None


def test_bootstrap_rejects_naive_scheduled_at(db_session: Session) -> None:
    _, person = _family_person(db_session, key="naive")

    response = _get(db_session, person, "2026-08-22T12:00:00")

    assert response.status_code == 422
    assert response.json()["detail"] == "scheduled_at must be timezone-aware."
