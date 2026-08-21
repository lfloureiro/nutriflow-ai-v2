from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.family import Family
from app.models.meal import MealEvent, MealParticipant, Serving, ServingNutritionComponent
from app.models.person import Person
from app.services.meal_lifecycle import (
    MealEventSpec,
    MealIdempotencyConflictError,
    MealReplacementError,
    create_idempotent_meal_event,
    replace_meal_event_plan,
)

BASE_TIME = datetime(2026, 8, 22, 19, 30, tzinfo=UTC)


def _family(db_session: Session, name: str = "Lifecycle Family") -> Family:
    family = Family(name=name, timezone="Europe/Lisbon")
    db_session.add(family)
    db_session.flush()
    return family


def _planned_event(db_session: Session) -> tuple[Family, Person, MealEvent]:
    family = Family(name="Replacement Family", timezone="Europe/Lisbon")
    person = Person(
        family=family,
        first_name="Ana",
        preferred_locale="pt-PT",
        timezone="Europe/Lisbon",
    )
    event = MealEvent(
        family=family,
        meal_type="dinner",
        title="Original dinner",
        scheduled_at=BASE_TIME,
        timezone="Europe/Lisbon",
        status="planned",
        source="user",
    )
    participant = MealParticipant(
        meal_event=event,
        person=person,
        status="planned",
    )
    Serving(
        meal_participant=participant,
        item_type="dish",
        item_key="dish:pasta",
        item_name="Pasta",
        status="planned",
        quantity_planned=Decimal("200.0000"),
        quantity_unit="g",
        energy_planned_kcal=Decimal("450.00"),
        nutrition_source="catalog",
        nutrition_calculation_version="serving-nutrition-v1",
        source_reference="test:pasta",
        nutrition_components=[
            ServingNutritionComponent(
                nutrient_key="protein",
                planned_value=Decimal("20.0000"),
                unit="g",
            )
        ],
    )
    db_session.add(family)
    db_session.flush()
    return family, person, event


def test_idempotent_creation_returns_existing_event_on_retry(db_session: Session) -> None:
    family = _family(db_session)
    if family.id is None:
        raise AssertionError("Family must be persisted.")

    spec = MealEventSpec(
        family_id=family.id,
        meal_type="lunch",
        title="Work lunch",
        scheduled_at=BASE_TIME,
        timezone="Europe/Lisbon",
        location="Office",
        source="api",
        source_reference="request:123",
    )

    first = create_idempotent_meal_event(
        db_session,
        spec=spec,
        idempotency_key="meal-create-123",
    )
    db_session.flush()
    second = create_idempotent_meal_event(
        db_session,
        spec=spec,
        idempotency_key="meal-create-123",
    )

    assert first.created is True
    assert second.created is False
    assert second.meal_event.id == first.meal_event.id
    assert db_session.scalar(select(func.count(MealEvent.id))) == 1


def test_idempotency_key_rejects_different_request_payload(db_session: Session) -> None:
    family = _family(db_session)
    if family.id is None:
        raise AssertionError("Family must be persisted.")

    first_spec = MealEventSpec(
        family_id=family.id,
        meal_type="lunch",
        title="First title",
        scheduled_at=BASE_TIME,
        timezone="Europe/Lisbon",
    )
    create_idempotent_meal_event(
        db_session,
        spec=first_spec,
        idempotency_key="same-key",
    )
    db_session.flush()

    conflicting_spec = MealEventSpec(
        family_id=family.id,
        meal_type="lunch",
        title="Different title",
        scheduled_at=BASE_TIME,
        timezone="Europe/Lisbon",
    )
    with pytest.raises(MealIdempotencyConflictError, match="different MealEvent request"):
        create_idempotent_meal_event(
            db_session,
            spec=conflicting_spec,
            idempotency_key="same-key",
        )


def test_replacement_preserves_old_event_and_clones_planned_content(db_session: Session) -> None:
    family, person, original = _planned_event(db_session)
    if family.id is None or original.id is None:
        raise AssertionError("Replacement fixtures must be persisted.")

    replacement_spec = MealEventSpec(
        family_id=family.id,
        replaces_meal_event_id=original.id,
        meal_type="dinner",
        title="Later dinner",
        scheduled_at=BASE_TIME + timedelta(hours=1),
        timezone="Europe/Lisbon",
        location="Home",
        source="replacement",
        source_reference=f"meal-event:{original.id}",
        notes="Moved one hour later",
    )
    result = replace_meal_event_plan(
        db_session,
        original=original,
        replacement_spec=replacement_spec,
        idempotency_key="replace-dinner-1",
    )
    db_session.flush()

    replacement = result.meal_event
    assert result.created is True
    assert original.status == "replaced"
    assert replacement.status == "planned"
    assert replacement.replaces_meal_event_id == original.id
    assert replacement.id != original.id
    assert len(replacement.participants) == 1
    cloned_participant = replacement.participants[0]
    assert cloned_participant.person_id == person.id
    assert cloned_participant.status == "planned"
    assert len(cloned_participant.servings) == 1

    cloned_serving = cloned_participant.servings[0]
    assert cloned_serving.item_key == "dish:pasta"
    assert cloned_serving.quantity_planned == Decimal("200.0000")
    assert cloned_serving.quantity_served is None
    assert cloned_serving.quantity_consumed is None
    assert cloned_serving.energy_planned_kcal == Decimal("450.00")
    assert cloned_serving.energy_served_kcal is None
    assert cloned_serving.energy_consumed_kcal is None
    assert cloned_serving.nutrition_components[0].nutrient_key == "protein"
    assert cloned_serving.nutrition_components[0].planned_value == Decimal("20.0000")
    assert db_session.scalar(select(func.count(MealEvent.id))) == 2


def test_replacement_retry_returns_same_replacement_without_duplicate(db_session: Session) -> None:
    family, _, original = _planned_event(db_session)
    if family.id is None or original.id is None:
        raise AssertionError("Replacement fixtures must be persisted.")

    spec = MealEventSpec(
        family_id=family.id,
        replaces_meal_event_id=original.id,
        meal_type="dinner",
        title="Replacement dinner",
        scheduled_at=BASE_TIME + timedelta(minutes=30),
        timezone="Europe/Lisbon",
        source="replacement",
        source_reference=f"meal-event:{original.id}",
    )
    first = replace_meal_event_plan(
        db_session,
        original=original,
        replacement_spec=spec,
        idempotency_key="replacement-retry-key",
    )
    db_session.flush()
    second = replace_meal_event_plan(
        db_session,
        original=original,
        replacement_spec=spec,
        idempotency_key="replacement-retry-key",
    )

    assert first.created is True
    assert second.created is False
    assert second.meal_event.id == first.meal_event.id
    assert original.status == "replaced"
    assert db_session.scalar(select(func.count(MealEvent.id))) == 2


def test_already_replaced_event_rejects_different_replacement_request(db_session: Session) -> None:
    family, _, original = _planned_event(db_session)
    if family.id is None or original.id is None:
        raise AssertionError("Replacement fixtures must be persisted.")

    first_spec = MealEventSpec(
        family_id=family.id,
        replaces_meal_event_id=original.id,
        meal_type="dinner",
        scheduled_at=BASE_TIME + timedelta(minutes=30),
        timezone="Europe/Lisbon",
        source="replacement",
    )
    replace_meal_event_plan(
        db_session,
        original=original,
        replacement_spec=first_spec,
        idempotency_key="replacement-first",
    )
    db_session.flush()

    second_spec = MealEventSpec(
        family_id=family.id,
        replaces_meal_event_id=original.id,
        meal_type="dinner",
        scheduled_at=BASE_TIME + timedelta(hours=2),
        timezone="Europe/Lisbon",
        source="replacement",
    )
    with pytest.raises(MealReplacementError, match="already replaced"):
        replace_meal_event_plan(
            db_session,
            original=original,
            replacement_spec=second_spec,
            idempotency_key="replacement-second",
        )


def test_served_event_cannot_be_replaced_as_plan(db_session: Session) -> None:
    family, _, original = _planned_event(db_session)
    if family.id is None or original.id is None:
        raise AssertionError("Replacement fixtures must be persisted.")
    original.status = "served"
    original.served_at = BASE_TIME

    spec = MealEventSpec(
        family_id=family.id,
        replaces_meal_event_id=original.id,
        meal_type="dinner",
        scheduled_at=BASE_TIME + timedelta(hours=1),
        timezone="Europe/Lisbon",
        source="replacement",
    )
    with pytest.raises(MealReplacementError, match="Only planned or prepared"):
        replace_meal_event_plan(
            db_session,
            original=original,
            replacement_spec=spec,
            idempotency_key="cannot-replace-served",
        )
