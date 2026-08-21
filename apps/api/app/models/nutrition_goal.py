import uuid
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Date, ForeignKey, Index, Numeric, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.person import Person


class NutritionGoal(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "nutrition_goals"

    __table_args__ = (
        CheckConstraint(
            "target_weight_kg IS NULL OR target_weight_kg > 0",
            name="ck_nutrition_goals_target_weight_positive",
        ),
        CheckConstraint(
            "target_rate_kg_per_week IS NULL OR target_rate_kg_per_week > 0",
            name="ck_nutrition_goals_target_rate_positive",
        ),
        CheckConstraint(
            "target_date IS NULL OR target_date >= start_date",
            name="ck_nutrition_goals_target_date_after_start",
        ),
        Index(
            "ix_nutrition_goals_person_status",
            "person_id",
            "status",
        ),
    )

    person_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("persons.id", ondelete="CASCADE"),
        nullable=False,
    )

    goal_type: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
    )

    target_weight_kg: Mapped[Decimal | None] = mapped_column(
        Numeric(8, 3),
        nullable=True,
    )

    target_rate_kg_per_week: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 3),
        nullable=True,
    )

    start_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    target_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        default="active",
    )

    source: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="user",
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    person: Mapped["Person"] = relationship(
        back_populates="nutrition_goals"
    )
