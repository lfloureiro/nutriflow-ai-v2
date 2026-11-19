import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Date,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class FamilyWeekSetup(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "family_week_setups"
    __table_args__ = (
        UniqueConstraint("family_id", "week_start", name="uq_family_week_setups_week"),
        CheckConstraint("version > 0", name="ck_family_week_setups_version"),
    )
    family_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("families.id", ondelete="CASCADE"),
        nullable=False,
    )
    week_start: Mapped[date] = mapped_column(Date, nullable=False)
    settings: Mapped[dict] = mapped_column(JSON, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class RetailAlternative(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "retail_alternatives"
    __table_args__ = (
        UniqueConstraint("product_key", name="uq_retail_alternatives_key"),
        CheckConstraint("pack_quantity > 0", name="ck_retail_alternatives_pack"),
        CheckConstraint(
            "observed_price IS NULL OR observed_price >= 0", name="ck_retail_alternatives_price"
        ),
    )
    product_key: Mapped[str] = mapped_column(String(100), nullable=False)
    retailer: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    alternative_group: Mapped[str] = mapped_column(String(80), nullable=False)
    source_food_catalog_keys: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    product_url: Mapped[str] = mapped_column(String(800), nullable=False)
    pack_quantity: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    pack_unit: Mapped[str] = mapped_column(String(24), nullable=False)
    ingredient_summary: Mapped[str] = mapped_column(Text, nullable=False)
    nutrition_per_100: Mapped[dict | None] = mapped_column(JSON)
    evidence_level: Mapped[str] = mapped_column(String(40), nullable=False)
    observed_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    observed_on: Mapped[date] = mapped_column(Date, nullable=False)
    notes: Mapped[str] = mapped_column(Text, nullable=False)
