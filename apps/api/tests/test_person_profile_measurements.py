from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.anthropometric_measurement import AnthropometricMeasurement
from app.models.family import Family
from app.models.person import Person
from app.models.person_profile import PersonProfile


def test_person_profile_and_anthropometric_history(db_session: Session) -> None:
    family = Family(
        name="Nutrition Test Family",
        timezone="Europe/Lisbon",
    )

    person = Person(
        family=family,
        first_name="Test",
        last_name="Person",
        birth_date=date(1990, 1, 1),
        preferred_locale="pt-PT",
        timezone="Europe/Lisbon",
    )

    profile = PersonProfile(
        person=person,
        sex_for_energy_calculation="male",
    )

    newer_weight = AnthropometricMeasurement(
        person=person,
        metric="weight",
        value=Decimal("102.4000"),
        unit="kg",
        measured_at=datetime(2026, 8, 21, 8, 0, tzinfo=UTC),
    )

    older_weight = AnthropometricMeasurement(
        person=person,
        metric="weight",
        value=Decimal("103.0000"),
        unit="kg",
        measured_at=datetime(2026, 8, 14, 8, 0, tzinfo=UTC),
    )

    db_session.add(person)
    db_session.flush()

    assert person.id is not None

    assert profile.person_id == person.id
    assert person.profile is profile
    assert profile.measurement_system == "metric"
    assert profile.energy_unit == "kcal"

    assert older_weight.id is not None
    assert newer_weight.id is not None
    assert older_weight.source == "manual"
    assert newer_weight.source == "manual"

    db_session.expire(person, ["anthropometric_measurements"])

    measurements = person.anthropometric_measurements

    assert len(measurements) == 2

    assert measurements[0].value == Decimal("103.0000")
    assert measurements[0].measured_at == datetime(2026, 8, 14, 8, 0, tzinfo=UTC)

    assert measurements[1].value == Decimal("102.4000")
    assert measurements[1].measured_at == datetime(2026, 8, 21, 8, 0, tzinfo=UTC)
