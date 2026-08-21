import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.person import Person


class PersonProfile(TimestampMixin, Base):
    __tablename__ = "person_profiles"

    person_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("persons.id", ondelete="CASCADE"),
        primary_key=True,
    )

    sex_for_energy_calculation: Mapped[str | None] = mapped_column(
        String(16),
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
