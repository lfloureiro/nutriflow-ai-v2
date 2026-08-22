import uuid
from datetime import date, datetime, time
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
    Text,
    Time,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.family import Family
    from app.models.food_catalog import FoodItem, Recipe


AVAILABILITY_KINDS = frozenset({"home", "pantry", "restaurant", "delivery", "store"})
COMMERCIAL_AVAILABILITY_KINDS = frozenset({"restaurant", "delivery", "store"})


class MealCandidateAvailability(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "meal_candidate_availability"
    __table_args__ = (
        CheckConstraint(
            "candidate_kind IN ('food_item', 'recipe')",
            name="ck_meal_candidate_availability_candidate_kind_valid",
        ),
        CheckConstraint(
            "source_kind IN ('home', 'pantry', 'restaurant', 'delivery', 'store')",
            name="ck_meal_candidate_availability_source_kind_valid",
        ),
        CheckConstraint(
            "length(source_key) > 0",
            name="ck_meal_candidate_availability_source_key_nonempty",
        ),
        CheckConstraint(
            "preparation_minutes IS NULL OR preparation_minutes >= 0",
            name="ck_meal_candidate_availability_preparation_nonnegative",
        ),
        CheckConstraint(
            "(candidate_kind = 'food_item' AND food_item_id IS NOT NULL AND recipe_id IS NULL) "
            "OR (candidate_kind = 'recipe' AND food_item_id IS NULL AND recipe_id IS NOT NULL)",
            name="ck_meal_candidate_availability_catalog_shape_valid",
        ),
        Index(
            "ix_meal_candidate_availability_family_kind",
            "family_id",
            "source_kind",
        ),
        Index(
            "ix_meal_candidate_availability_food_item",
            "food_item_id",
        ),
        Index(
            "ix_meal_candidate_availability_recipe",
            "recipe_id",
        ),
    )

    family_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("families.id", ondelete="CASCADE"),
        nullable=False,
    )
    food_item_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("food_items.id", ondelete="CASCADE"),
        nullable=True,
    )
    recipe_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("recipes.id", ondelete="CASCADE"),
        nullable=True,
    )

    candidate_kind: Mapped[str] = mapped_column(String(24), nullable=False)
    source_kind: Mapped[str] = mapped_column(String(24), nullable=False)
    source_key: Mapped[str] = mapped_column(String(160), nullable=False)
    location: Mapped[str | None] = mapped_column(String(160), nullable=True)
    preparation_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    requires_kitchen: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    source: Mapped[str] = mapped_column(String(32), nullable=False, default="user")
    source_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    family: Mapped["Family"] = relationship()
    food_item: Mapped["FoodItem | None"] = relationship()
    recipe: Mapped["Recipe | None"] = relationship()
    opening_windows: Mapped[list["MealSourceOpeningWindow"]] = relationship(
        back_populates="availability",
        cascade="all, delete-orphan",
        order_by=lambda: (
            MealSourceOpeningWindow.weekday,
            MealSourceOpeningWindow.local_start_time,
        ),
    )
    commercial_offers: Mapped[list["MealCommercialOffer"]] = relationship(
        back_populates="availability",
        cascade="all, delete-orphan",
        order_by=lambda: MealCommercialOffer.offer_key,
    )


class MealSourceOpeningWindow(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "meal_source_opening_windows"
    __table_args__ = (
        CheckConstraint(
            "weekday >= 0 AND weekday <= 6",
            name="ck_meal_source_opening_windows_weekday_valid",
        ),
        CheckConstraint(
            "length(timezone) > 0",
            name="ck_meal_source_opening_windows_timezone_nonempty",
        ),
        CheckConstraint(
            "valid_until IS NULL OR valid_from IS NULL OR valid_until >= valid_from",
            name="ck_meal_source_opening_windows_valid_range",
        ),
        Index(
            "ix_meal_source_opening_windows_availability_weekday",
            "availability_id",
            "weekday",
        ),
    )

    availability_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("meal_candidate_availability.id", ondelete="CASCADE"),
        nullable=False,
    )
    weekday: Mapped[int] = mapped_column(Integer, nullable=False)
    local_start_time: Mapped[time] = mapped_column(Time(), nullable=False)
    local_end_time: Mapped[time] = mapped_column(Time(), nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False)
    valid_from: Mapped[date | None] = mapped_column(Date(), nullable=True)
    valid_until: Mapped[date | None] = mapped_column(Date(), nullable=True)

    source: Mapped[str] = mapped_column(String(32), nullable=False, default="user")
    source_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    availability: Mapped[MealCandidateAvailability] = relationship(
        back_populates="opening_windows"
    )


class MealCommercialOffer(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "meal_commercial_offers"
    __table_args__ = (
        CheckConstraint(
            "length(offer_key) > 0",
            name="ck_meal_commercial_offers_offer_key_nonempty",
        ),
        CheckConstraint(
            "length(provider_key) > 0",
            name="ck_meal_commercial_offers_provider_key_nonempty",
        ),
        CheckConstraint(
            "length(currency) = 3",
            name="ck_meal_commercial_offers_currency_length",
        ),
        CheckConstraint(
            "item_price >= 0",
            name="ck_meal_commercial_offers_item_price_nonnegative",
        ),
        CheckConstraint(
            "delivery_fee IS NULL OR delivery_fee >= 0",
            name="ck_meal_commercial_offers_delivery_fee_nonnegative",
        ),
        CheckConstraint(
            "minimum_order IS NULL OR minimum_order >= 0",
            name="ck_meal_commercial_offers_minimum_order_nonnegative",
        ),
        CheckConstraint(
            "valid_until IS NULL OR valid_from IS NULL OR valid_until > valid_from",
            name="ck_meal_commercial_offers_valid_range",
        ),
        UniqueConstraint(
            "family_id",
            "offer_key",
            name="uq_meal_commercial_offers_family_offer_key",
        ),
        Index(
            "ix_meal_commercial_offers_availability",
            "availability_id",
        ),
        Index(
            "ix_meal_commercial_offers_family_provider",
            "family_id",
            "provider_key",
        ),
    )

    family_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("families.id", ondelete="CASCADE"),
        nullable=False,
    )
    availability_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("meal_candidate_availability.id", ondelete="CASCADE"),
        nullable=False,
    )

    offer_key: Mapped[str] = mapped_column(String(160), nullable=False)
    provider_key: Mapped[str] = mapped_column(String(120), nullable=False)
    provider_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    item_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    delivery_fee: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    minimum_order: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    is_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    source: Mapped[str] = mapped_column(String(32), nullable=False, default="provider")
    source_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    availability: Mapped[MealCandidateAvailability] = relationship(
        back_populates="commercial_offers"
    )
