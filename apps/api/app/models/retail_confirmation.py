import uuid

from sqlalchemy import JSON, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class RetailIngredientConfirmation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "retail_ingredient_confirmations"
    __table_args__ = (
        UniqueConstraint(
            "family_id",
            "retail_product_id",
            "label_fingerprint",
            name="uq_retail_confirmations_family_product_label",
        ),
        UniqueConstraint("food_item_id", name="uq_retail_confirmations_food"),
    )
    family_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("families.id", ondelete="CASCADE"))
    retail_product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("retail_alternatives.id", ondelete="RESTRICT"), index=True
    )
    food_item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("food_items.id", ondelete="RESTRICT")
    )
    label_fingerprint: Mapped[str] = mapped_column(String(64))
    food_fingerprint: Mapped[str] = mapped_column(String(64))
    evidence: Mapped[dict] = mapped_column(JSON)
    retail_product = relationship("RetailAlternative")
    food_item = relationship("FoodItem")
