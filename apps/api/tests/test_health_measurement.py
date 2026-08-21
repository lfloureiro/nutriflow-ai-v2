from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.family import Family
from app.models.health_connection import HealthConnection
from app.models.health_measurement import HealthMeasurement
from app.models.person import Person


def test_health_measurements_preserve_provenance_and_prevent_duplicate_paths(
    db_session: Session,
) -> None:
    family = Family(name="Health Measurement Test Family", timezone="Europe/Lisbon")
    person = Person(
        family=family,
        first_name="Health",
        last_name="Tester",
        birth_date=date(1990, 1, 1),
        preferred_locale="pt-PT",
        timezone="Europe/Lisbon",
    )
    connection = HealthConnection(
        person=person,
        provider="apple_health",
        connection_key="iphone-primary",
        connection_kind="device_bridge",
        status="active",
        permissions=["active_energy", "resting_heart_rate"],
    )

    active_energy = HealthMeasurement(
        person=person,
        health_connection=connection,
        metric="active_energy",
        value=Decimal("450.0000"),
        unit="kcal",
        period_start_at=datetime(2026, 8, 21, 8, 0, tzinfo=UTC),
        period_end_at=datetime(2026, 8, 21, 12, 0, tzinfo=UTC),
        provider="apple_health",
        origin_provider="garmin",
        source_kind="device",
        source_device="Garmin Watch",
        source_app="Garmin Connect",
        external_id="apple-health-record-123",
        origin_external_id="garmin-activity-456",
        deduplication_key="garmin:activity:456",
        source_chain=["garmin_watch", "garmin_connect", "apple_health"],
        provenance_metadata={"import_path": "healthkit"},
        normalization_version="health-v1",
    )
    resting_heart_rate = HealthMeasurement(
        person=person,
        health_connection=connection,
        metric="resting_heart_rate",
        value=Decimal("62.0000"),
        unit="bpm",
        observed_at=datetime(2026, 8, 21, 7, 30, tzinfo=UTC),
        provider="apple_health",
        origin_provider="apple_health",
        source_kind="device",
        source_device="Apple Watch",
        external_id="apple-rhr-789",
        origin_external_id="apple-rhr-789",
        deduplication_key="apple_health:rhr:789",
        source_chain=["apple_watch", "apple_health"],
        normalization_version="health-v1",
    )

    db_session.add(person)
    db_session.flush()

    assert person.id is not None
    assert connection.id is not None
    assert active_energy.id is not None
    assert resting_heart_rate.id is not None

    assert active_energy.health_connection_id == connection.id
    assert active_energy.origin_provider == "garmin"
    assert active_energy.origin_external_id == "garmin-activity-456"
    assert active_energy.source_chain == [
        "garmin_watch",
        "garmin_connect",
        "apple_health",
    ]
    assert active_energy.normalization_version == "health-v1"
    assert resting_heart_rate.observed_at == datetime(2026, 8, 21, 7, 30, tzinfo=UTC)
    assert resting_heart_rate.period_start_at is None

    db_session.expire(person, ["health_measurements"])
    assert len(person.health_measurements) == 2

    with pytest.raises(IntegrityError):
        with db_session.begin_nested():
            duplicate_via_direct_garmin = HealthMeasurement(
                person_id=person.id,
                metric="active_energy",
                value=Decimal("450.0000"),
                unit="kcal",
                period_start_at=datetime(2026, 8, 21, 8, 0, tzinfo=UTC),
                period_end_at=datetime(2026, 8, 21, 12, 0, tzinfo=UTC),
                provider="garmin",
                origin_provider="garmin",
                source_kind="provider",
                external_id="garmin-activity-456",
                origin_external_id="garmin-activity-456",
                deduplication_key="garmin:activity:456",
                source_chain=["garmin_connect"],
                normalization_version="health-v1",
            )
            db_session.add(duplicate_via_direct_garmin)
            db_session.flush()

    db_session.expire(person, ["health_measurements"])
    assert len(person.health_measurements) == 2
