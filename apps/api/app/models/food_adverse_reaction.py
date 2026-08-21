import uuid
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, Date, ForeignKey, Index, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.person import Person


class FoodAdverseReaction(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "food_adverse_reactions"

    __table_args__ = (
        CheckConstraint(
            "start_date IS NULL OR end_date IS NULL OR end_date >= start_date",
            name="ck_food_adverse_reactions_date_range_valid",
        ),
        Index(
            "ix_food_adverse_reactions_person_subject",
            "person_id",
            "subject_type",
            "subject_key",
            "reaction_type",
        ),
    )

    person_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("persons.id", ondelete="CASCADE"),
        nullable=False,
    )

    reaction_type: Mapped[str] = mapped_column(String(24), nullable=False)
    subject_type: Mapped[str] = mapped_column(String(32), nullable=False)
    subject_key: Mapped[str] = mapped_column(String(120), nullable=False)

    severity: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        default="moderate",
    )
    is_mandatory: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    source: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="user",
    )
    source_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    source_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)

    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    person: Mapped["Person"] = relationship(back_populates="food_adverse_reactions")
