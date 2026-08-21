import uuid
from datetime import date, datetime, time
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Time,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.person import Person


class ScheduleEntry(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "schedule_entries"

    __table_args__ = (
        CheckConstraint(
            "entry_type IN ('recurring', 'one_off')",
            name="ck_schedule_entries_entry_type_valid",
        ),
        CheckConstraint(
            "availability_effect IN ('neutral', 'available', 'unavailable', 'preferred')",
            name="ck_schedule_entries_availability_effect_valid",
        ),
        CheckConstraint(
            "flexibility_minutes >= 0",
            name="ck_schedule_entries_flexibility_nonnegative",
        ),
        CheckConstraint(
            "starts_at IS NULL OR ends_at IS NULL OR ends_at > starts_at",
            name="ck_schedule_entries_one_off_time_range_valid",
        ),
        CheckConstraint(
            "valid_from IS NULL OR valid_until IS NULL OR valid_until >= valid_from",
            name="ck_schedule_entries_validity_range_valid",
        ),
        CheckConstraint(
            "(entry_type = 'one_off' "
            "AND starts_at IS NOT NULL "
            "AND ends_at IS NOT NULL "
            "AND local_start_time IS NULL "
            "AND local_end_time IS NULL "
            "AND recurrence_rule IS NULL "
            "AND valid_from IS NULL "
            "AND valid_until IS NULL) "
            "OR "
            "(entry_type = 'recurring' "
            "AND starts_at IS NULL "
            "AND ends_at IS NULL "
            "AND local_start_time IS NOT NULL "
            "AND local_end_time IS NOT NULL "
            "AND recurrence_rule IS NOT NULL "
            "AND valid_from IS NOT NULL)",
            name="ck_schedule_entries_entry_shape_valid",
        ),
        Index(
            "ix_schedule_entries_person_type_event",
            "person_id",
            "entry_type",
            "event_type",
        ),
    )

    person_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("persons.id", ondelete="CASCADE"),
        nullable=False,
    )

    entry_type: Mapped[str] = mapped_column(String(16), nullable=False)
    event_type: Mapped[str] = mapped_column(String(40), nullable=False)
    availability_effect: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="neutral",
    )

    starts_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    ends_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    local_start_time: Mapped[time | None] = mapped_column(Time(timezone=False), nullable=True)
    local_end_time: Mapped[time | None] = mapped_column(Time(timezone=False), nullable=True)
    recurrence_rule: Mapped[str | None] = mapped_column(Text, nullable=True)
    valid_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)

    timezone: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="Europe/Lisbon",
    )
    flexibility_minutes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="user",
    )
    source_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    person: Mapped["Person"] = relationship(back_populates="schedule_entries")
