from datetime import UTC, date, datetime, time

from sqlalchemy.orm import Session

from app.models.family import Family
from app.models.person import Person
from app.models.schedule_entry import ScheduleEntry


def test_person_schedule_supports_recurring_and_one_off_entries(db_session: Session) -> None:
    family = Family(
        name="Schedule Test Family",
        timezone="Europe/Lisbon",
    )

    person = Person(
        family=family,
        first_name="Schedule",
        last_name="Tester",
        birth_date=date(1990, 1, 1),
        preferred_locale="pt-PT",
        timezone="Europe/Lisbon",
    )

    recurring_work = ScheduleEntry(
        person=person,
        entry_type="recurring",
        event_type="work",
        availability_effect="unavailable",
        local_start_time=time(9, 0),
        local_end_time=time(17, 30),
        recurrence_rule="FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR",
        valid_from=date(2026, 8, 24),
        valid_until=date(2026, 12, 31),
        timezone="Europe/Lisbon",
        flexibility_minutes=30,
        location="Office",
    )

    one_off_training = ScheduleEntry(
        person=person,
        entry_type="one_off",
        event_type="training",
        starts_at=datetime(2026, 8, 25, 18, 0, tzinfo=UTC),
        ends_at=datetime(2026, 8, 25, 19, 0, tzinfo=UTC),
        timezone="Europe/Lisbon",
        notes="Indoor cycling",
    )

    db_session.add(person)
    db_session.flush()

    assert person.id is not None
    assert recurring_work.id is not None
    assert one_off_training.id is not None

    assert recurring_work.person_id == person.id
    assert recurring_work.entry_type == "recurring"
    assert recurring_work.availability_effect == "unavailable"
    assert recurring_work.source == "user"
    assert recurring_work.flexibility_minutes == 30

    assert one_off_training.person_id == person.id
    assert one_off_training.entry_type == "one_off"
    assert one_off_training.availability_effect == "neutral"
    assert one_off_training.source == "user"
    assert one_off_training.flexibility_minutes == 0

    db_session.expire(person, ["schedule_entries"])

    entries = person.schedule_entries
    assert len(entries) == 2

    entries_by_event = {entry.event_type: entry for entry in entries}

    assert entries_by_event["work"].recurrence_rule == "FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR"
    assert entries_by_event["work"].local_start_time == time(9, 0)
    assert entries_by_event["work"].local_end_time == time(17, 30)

    assert entries_by_event["training"].starts_at is not None
    assert entries_by_event["training"].ends_at is not None
    assert entries_by_event["training"].recurrence_rule is None
