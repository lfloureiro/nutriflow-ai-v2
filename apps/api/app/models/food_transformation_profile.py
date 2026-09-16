import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
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


class FoodTransformationProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "food_transformation_profiles"
    __table_args__ = (
        CheckConstraint(
            "length(substitution_group) > 0",
            name="ck_food_transformation_profiles_group_nonempty",
        ),
        CheckConstraint(
            "typical_quantity IS NULL OR typical_quantity > 0",
            name="ck_food_transformation_profiles_quantity_positive",
        ),
        CheckConstraint(
            "(typical_quantity IS NULL AND typical_unit IS NULL) "
            "OR (typical_quantity IS NOT NULL AND typical_unit IS NOT NULL)",
            name="ck_food_transformation_profiles_portion_shape",
        ),
        UniqueConstraint(
            "family_id",
            "food_item_id",
            name="uq_food_transformation_profiles_family_food",
        ),
        Index(
            "ix_food_transformation_profiles_family_group",
            "family_id",
            "substitution_group",
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
    substitution_group: Mapped[str] = mapped_column(String(64), nullable=False)
    typical_quantity: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    typical_unit: Mapped[str | None] = mapped_column(String(24), nullable=True)
    auto_transform_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="derived")
    source_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)

    family: Mapped["Family"] = relationship()
    food_item: Mapped["FoodItem"] = relationship()
