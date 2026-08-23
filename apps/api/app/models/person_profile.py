import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.person import Person


class PersonProfile(TimestampMixin, Base):
    __tablename__ = "person_profiles"
    __table_args__ = (
        CheckConstraint(
            "activity_level IS NULL OR activity_level IN "
            "('sedentary', 'light', 'moderate', 'active', 'very_active')",
            name="ck_person_profiles_activity_level_valid",
        ),
        CheckConstraint(
            "standard_breakfast_kcal IS NULL OR standard_breakfast_kcal > 0",
            name="ck_person_profiles_standard_breakfast_positive",
        ),
    )

    person_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("persons.id", ondelete="CASCADE"),
        primary_key=True,
    )

    sex_for_energy_calculation: Mapped[str | None] = mapped_column(
        String(16),
        nullable=True,
    )

    activity_level: Mapped[str | None] = mapped_column(
        String(24),
        nullable=True,
    )

    standard_breakfast_kcal: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
    )

    measurement_system: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="metric",
    )

    energy_unit: Mapped[str] = mapped_column(
        String(8),
        nullable=False,
        default="kcal",
    )

    person: Mapped["Person"] = relationship(back_populates="profile")
