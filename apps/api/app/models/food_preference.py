import uuid
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Date, ForeignKey, Index, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.person import Person


class FoodPreference(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "food_preferences"

    __table_args__ = (
        CheckConstraint(
            "intensity >= 0 AND intensity <= 5",
            name="ck_food_preferences_intensity_range",
        ),
        CheckConstraint(
            "start_date IS NULL OR end_date IS NULL OR end_date >= start_date",
            name="ck_food_preferences_date_range_valid",
        ),
        Index(
            "ix_food_preferences_person_subject",
            "person_id",
            "subject_type",
            "subject_key",
        ),
    )

    person_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("persons.id", ondelete="CASCADE"),
        nullable=False,
    )

    subject_type: Mapped[str] = mapped_column(String(32), nullable=False)
    subject_key: Mapped[str] = mapped_column(String(120), nullable=False)
    preference_type: Mapped[str] = mapped_column(String(16), nullable=False)
    intensity: Mapped[int] = mapped_column(Integer, nullable=False, default=3)

    source: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="user",
    )

    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    person: Mapped["Person"] = relationship(back_populates="food_preferences")
