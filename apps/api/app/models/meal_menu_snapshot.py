import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.family import Family
    from app.models.food_catalog import FoodItem


class MealMenuSnapshot(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One dated observation of a merchant menu.

    Snapshots are intentionally historical. Current availability is kept on
    MealCandidateAvailability/MealCommercialOffer, while these rows provide the evidence
    needed to learn recurring daily/weekly menu patterns without losing older dishes.
    """

    __tablename__ = "meal_menu_snapshots"
    __table_args__ = (
        CheckConstraint(
            "source_kind IN ('restaurant', 'delivery')",
            name="ck_meal_menu_snapshots_source_kind_valid",
        ),
        CheckConstraint(
            "weekday >= 0 AND weekday <= 6",
            name="ck_meal_menu_snapshots_weekday_valid",
        ),
        CheckConstraint(
            "item_count >= 0",
            name="ck_meal_menu_snapshots_item_count_nonnegative",
        ),
        Index(
            "ix_meal_menu_snapshots_family_merchant_date",
            "family_id",
            "provider_key",
            "merchant_key",
            "observed_local_date",
        ),
        Index(
            "ix_meal_menu_snapshots_family_merchant_weekday",
            "family_id",
            "provider_key",
            "merchant_key",
            "weekday",
        ),
    )

    family_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("families.id", ondelete="CASCADE"),
        nullable=False,
    )
    provider_key: Mapped[str] = mapped_column(String(120), nullable=False)
    merchant_key: Mapped[str] = mapped_column(String(160), nullable=False)
    merchant_name: Mapped[str] = mapped_column(String(160), nullable=False)
    source_kind: Mapped[str] = mapped_column(String(24), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    observed_local_date: Mapped[date] = mapped_column(Date(), nullable=False)
    weekday: Mapped[int] = mapped_column(Integer, nullable=False)
    item_count: Mapped[int] = mapped_column(Integer, nullable=False)
    is_complete: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    query: Mapped[str | None] = mapped_column(String(160), nullable=True)
    source_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)

    family: Mapped["Family"] = relationship()
    items: Mapped[list["MealMenuSnapshotItem"]] = relationship(
        back_populates="snapshot",
        cascade="all, delete-orphan",
        order_by=lambda: MealMenuSnapshotItem.item_name,
    )


class MealMenuSnapshotItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "meal_menu_snapshot_items"
    __table_args__ = (
        UniqueConstraint(
            "snapshot_id",
            "item_key",
            name="uq_meal_menu_snapshot_items_snapshot_item_key",
        ),
        CheckConstraint(
            "item_price >= 0",
            name="ck_meal_menu_snapshot_items_price_nonnegative",
        ),
        CheckConstraint(
            "length(currency) = 3",
            name="ck_meal_menu_snapshot_items_currency_length",
        ),
        Index(
            "ix_meal_menu_snapshot_items_food_item",
            "food_item_id",
        ),
    )

    snapshot_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("meal_menu_snapshots.id", ondelete="CASCADE"),
        nullable=False,
    )
    food_item_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("food_items.id", ondelete="CASCADE"),
        nullable=False,
    )
    item_key: Mapped[str] = mapped_column(String(160), nullable=False)
    item_name: Mapped[str] = mapped_column(String(160), nullable=False)
    item_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    source_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)

    snapshot: Mapped[MealMenuSnapshot] = relationship(back_populates="items")
    food_item: Mapped["FoodItem"] = relationship()
