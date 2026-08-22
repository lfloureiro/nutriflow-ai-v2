import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.family import Family
    from app.models.food_catalog import FoodItem


class PantryStockLot(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "pantry_stock_lots"
    __table_args__ = (
        CheckConstraint(
            "length(stock_key) > 0",
            name="ck_pantry_stock_lots_stock_key_nonempty",
        ),
        CheckConstraint(
            "quantity_available > 0",
            name="ck_pantry_stock_lots_quantity_positive",
        ),
        CheckConstraint(
            "length(unit) > 0",
            name="ck_pantry_stock_lots_unit_nonempty",
        ),
        CheckConstraint(
            "length(source) > 0",
            name="ck_pantry_stock_lots_source_nonempty",
        ),
        UniqueConstraint(
            "family_id",
            "stock_key",
            name="uq_pantry_stock_lots_family_stock_key",
        ),
        Index(
            "ix_pantry_stock_lots_family_food",
            "family_id",
            "food_item_id",
        ),
        Index(
            "ix_pantry_stock_lots_family_expiry",
            "family_id",
            "expires_at",
        ),
    )

    family_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("families.id", ondelete="CASCADE"),
        nullable=False,
    )
    food_item_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("food_items.id", ondelete="CASCADE"),
        nullable=False,
    )

    stock_key: Mapped[str] = mapped_column(String(160), nullable=False)
    quantity_available: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    unit: Mapped[str] = mapped_column(String(24), nullable=False)
    location: Mapped[str | None] = mapped_column(String(80), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    is_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    source: Mapped[str] = mapped_column(String(32), nullable=False, default="user")
    source_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    family: Mapped["Family"] = relationship()
    food_item: Mapped["FoodItem"] = relationship()
