import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.family import Family
    from app.models.food_catalog import FoodItem


class ShoppingList(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "shopping_lists"
    __table_args__ = (
        CheckConstraint("length(list_key) > 0", name="ck_shopping_lists_key_nonempty"),
        CheckConstraint(
            "status IN ('active', 'archived')",
            name="ck_shopping_lists_status_valid",
        ),
        CheckConstraint("length(source) > 0", name="ck_shopping_lists_source_nonempty"),
        UniqueConstraint("family_id", "list_key", name="uq_shopping_lists_family_key"),
        Index("ix_shopping_lists_family_status", "family_id", "status"),
    )

    family_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("families.id", ondelete="CASCADE"),
        nullable=False,
    )
    list_key: Mapped[str] = mapped_column(String(160), nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False, default="Compras")
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="active")
    planning_start: Mapped[date | None] = mapped_column(Date(), nullable=True)
    planning_end: Mapped[date | None] = mapped_column(Date(), nullable=True)
    generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="user")
    source_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)

    family: Mapped["Family"] = relationship()
    items: Mapped[list["ShoppingListItem"]] = relationship(
        back_populates="shopping_list",
        cascade="all, delete-orphan",
        order_by=lambda: (
            ShoppingListItem.status,
            ShoppingListItem.sort_order,
            ShoppingListItem.name,
        ),
    )


class ShoppingListItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "shopping_list_items"
    __table_args__ = (
        CheckConstraint("length(item_key) > 0", name="ck_shopping_list_items_key_nonempty"),
        CheckConstraint("length(name) > 0", name="ck_shopping_list_items_name_nonempty"),
        CheckConstraint(
            "item_source IN ('automatic', 'manual')",
            name="ck_shopping_list_items_source_valid",
        ),
        CheckConstraint(
            "status IN ('needed', 'purchased')",
            name="ck_shopping_list_items_status_valid",
        ),
        CheckConstraint(
            "(quantity IS NULL AND unit IS NULL) OR "
            "(quantity > 0 AND unit IS NOT NULL AND length(unit) > 0)",
            name="ck_shopping_list_items_quantity_unit_shape",
        ),
        CheckConstraint("sort_order >= 0", name="ck_shopping_list_items_sort_nonnegative"),
        UniqueConstraint(
            "shopping_list_id",
            "item_key",
            name="uq_shopping_list_items_list_key",
        ),
        Index("ix_shopping_list_items_list_status", "shopping_list_id", "status"),
        Index("ix_shopping_list_items_food", "food_item_id"),
    )

    shopping_list_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("shopping_lists.id", ondelete="CASCADE"),
        nullable=False,
    )
    food_item_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("food_items.id", ondelete="SET NULL"),
        nullable=True,
    )
    item_key: Mapped[str] = mapped_column(String(180), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(24), nullable=True)
    item_source: Mapped[str] = mapped_column(String(24), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="needed")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)

    shopping_list: Mapped[ShoppingList] = relationship(back_populates="items")
    food_item: Mapped["FoodItem | None"] = relationship()
