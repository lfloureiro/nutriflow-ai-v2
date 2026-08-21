import uuid
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.person import Person


class NutritionConstraint(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "nutrition_constraints"

    __table_args__ = (
        CheckConstraint(
            "value_min IS NULL OR value_min >= 0",
            name="ck_nutrition_constraints_value_min_nonnegative",
        ),
        CheckConstraint(
            "value_max IS NULL OR value_max >= 0",
            name="ck_nutrition_constraints_value_max_nonnegative",
        ),
        CheckConstraint(
            "value_min IS NULL OR value_max IS NULL OR value_max >= value_min",
            name="ck_nutrition_constraints_value_range_valid",
        ),
        CheckConstraint(
            "start_date IS NULL OR end_date IS NULL OR end_date >= start_date",
            name="ck_nutrition_constraints_date_range_valid",
        ),
        Index(
            "ix_nutrition_constraints_person_target",
            "person_id",
            "target_type",
            "target_key",
        ),
    )

    person_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("persons.id", ondelete="CASCADE"),
        nullable=False,
    )

    constraint_type: Mapped[str] = mapped_column(String(40), nullable=False)
    target_type: Mapped[str] = mapped_column(String(32), nullable=False)
    target_key: Mapped[str] = mapped_column(String(120), nullable=False)
    operator: Mapped[str] = mapped_column(String(24), nullable=False)

    value_min: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    value_max: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(24), nullable=True)

    severity: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        default="advisory",
    )
    is_mandatory: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
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

    person: Mapped["Person"] = relationship(back_populates="nutrition_constraints")
