import uuid
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.anthropometric_measurement import AnthropometricMeasurement
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.nutrition_goal import NutritionGoal
from app.models.person_profile import PersonProfile

if TYPE_CHECKING:
    from app.models.family import Family


class Person(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "persons"

    family_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("families.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    preferred_locale: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="pt-PT",
    )

    timezone: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="Europe/Lisbon",
    )

    family: Mapped["Family"] = relationship(back_populates="persons")

    profile: Mapped[PersonProfile | None] = relationship(
        back_populates="person",
        cascade="all, delete-orphan",
        single_parent=True,
        uselist=False,
    )

    anthropometric_measurements: Mapped[list[AnthropometricMeasurement]] = relationship(
        back_populates="person",
        cascade="all, delete-orphan",
        order_by=AnthropometricMeasurement.measured_at,
    )

    nutrition_goals: Mapped[list[NutritionGoal]] = relationship(
        back_populates="person",
        cascade="all, delete-orphan",
        order_by=NutritionGoal.start_date,
    )
