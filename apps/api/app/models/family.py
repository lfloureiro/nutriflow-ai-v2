from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.food_catalog import FoodItem, Recipe
from app.models.meal import MealEvent
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.person import Person


class Family(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "families"

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    timezone: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="Europe/Lisbon",
    )

    persons: Mapped[list["Person"]] = relationship(
        back_populates="family",
        cascade="all, delete-orphan",
    )

    meal_events: Mapped[list[MealEvent]] = relationship(
        back_populates="family",
        cascade="all, delete-orphan",
        order_by=MealEvent.scheduled_at,
    )

    food_items: Mapped[list[FoodItem]] = relationship(
        back_populates="family",
        order_by=FoodItem.name,
    )

    recipes: Mapped[list[Recipe]] = relationship(
        back_populates="family",
        order_by=Recipe.name,
    )
