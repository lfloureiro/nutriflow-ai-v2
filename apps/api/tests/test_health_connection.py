from datetime import UTC, date, datetime

from sqlalchemy.orm import Session

from app.models.family import Family
from app.models.health_connection import HealthConnection
from app.models.person import Person


def test_person_health_connections_are_provider_scoped(db_session: Session) -> None:
    family = Family(
        name="Health Connection Test Family",
        timezone="Europe/Lisbon",
    )

    person = Person(
        family=family,
        first_name="Health",
        last_name="Tester",
        birth_date=date(1990, 1, 1),
        preferred_locale="pt-PT",
        timezone="Europe/Lisbon",
    )

    healthkit = HealthConnection(
        person=person,
        provider="apple_healthkit",
        connection_key="iphone-primary",
        connection_kind="device_bridge",
    )

    sync_time = datetime(2026, 8, 21, 15, 30, tzinfo=UTC)
    garmin = HealthConnection(
        person=person,
        provider="garmin",
        connection_key="garmin-account-primary",
        connection_kind="cloud_api",
        status="active",
        permissions=["steps", "workouts", "active_energy"],
        provider_account_id="garmin-user-123",
        credential_reference="secret://health/garmin/connection-1",
        provider_metadata={"region": "eu"},
        sync_cursor="cursor-42",
        last_sync_attempt_at=sync_time,
        last_successful_sync_at=sync_time,
    )

    db_session.add(person)
    db_session.flush()

    assert person.id is not None
    assert healthkit.id is not None
    assert garmin.id is not None

    assert healthkit.person_id == person.id
    assert healthkit.status == "pending"
    assert healthkit.permissions == []
    assert healthkit.credential_reference is None

    assert garmin.person_id == person.id
    assert garmin.status == "active"
    assert garmin.permissions == ["steps", "workouts", "active_energy"]
    assert garmin.provider_account_id == "garmin-user-123"
    assert garmin.credential_reference == "secret://health/garmin/connection-1"
    assert garmin.last_successful_sync_at == sync_time

    db_session.expire(person, ["health_connections"])

    connections = {
        (connection.provider, connection.connection_key): connection
        for connection in person.health_connections
    }

    assert len(connections) == 2
    assert connections[("apple_healthkit", "iphone-primary")].connection_kind == "device_bridge"
    assert connections[("garmin", "garmin-account-primary")].connection_kind == "cloud_api"
    assert connections[("garmin", "garmin-account-primary")].sync_cursor == "cursor-42"
