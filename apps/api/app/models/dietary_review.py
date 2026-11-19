"""Reported conditions and educational food evidence; never implicit prescriptions."""

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class PersonHealthCondition(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "person_health_conditions"
    __table_args__ = (
        UniqueConstraint("person_id", "code", name="uq_person_health_conditions_person_code"),
        CheckConstraint("version > 0", name="ck_person_health_conditions_version"),
        CheckConstraint(
            "status IN ('reported','suspected','confirmed','resolved')",
            name="ck_person_health_conditions_status",
        ),
        CheckConstraint(
            "source IN ('user','doctor','nutritionist','document')",
            name="ck_person_health_conditions_source",
        ),
        CheckConstraint(
            "started_on IS NULL OR ended_on IS NULL OR ended_on >= started_on",
            name="ck_person_health_conditions_dates",
        ),
        Index("ix_person_health_conditions_person", "person_id"),
    )
    person_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("persons.id", ondelete="CASCADE"),
        nullable=False,
    )
    code: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    source: Mapped[str] = mapped_column(String(24), nullable=False)
    source_reference: Mapped[str | None] = mapped_column(String(500))
    started_on: Mapped[date | None] = mapped_column(Date)
    ended_on: Mapped[date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class PersonHealthConditionEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "person_health_condition_events"
    __table_args__ = (
        UniqueConstraint("condition_id", "version", name="uq_health_condition_events_version"),
    )
    condition_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("person_health_conditions.id", ondelete="CASCADE"),
        nullable=False,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)


class FodmapReference(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "fodmap_references"
    __table_args__ = (
        UniqueConstraint("reference_key", name="uq_fodmap_references_key"),
        CheckConstraint(
            "classification IN ('high','low','variable','unknown')",
            name="ck_fodmap_references_classification",
        ),
    )
    reference_key: Mapped[str] = mapped_column(String(100), nullable=False)
    name_pt: Mapped[str] = mapped_column(String(160), nullable=False)
    name_en: Mapped[str] = mapped_column(String(160), nullable=False)
    classification: Mapped[str] = mapped_column(String(24), nullable=False)
    fodmap_groups: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    preparation: Mapped[str] = mapped_column(String(160), nullable=False)
    evidence_kind: Mapped[str] = mapped_column(String(40), nullable=False)
    source_name: Mapped[str] = mapped_column(String(160), nullable=False)
    source_url: Mapped[str] = mapped_column(String(500), nullable=False)
    source_version: Mapped[str] = mapped_column(String(80), nullable=False)
    retrieved_on: Mapped[date] = mapped_column(Date, nullable=False)
    notes_pt: Mapped[str] = mapped_column(Text, nullable=False)
    notes_en: Mapped[str] = mapped_column(Text, nullable=False)


class FoodFodmapReference(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "food_fodmap_references"
    __table_args__ = (
        UniqueConstraint("food_item_id", "reference_id", name="uq_food_fodmap_references_link"),
    )
    food_item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("food_items.id", ondelete="CASCADE"),
        nullable=False,
    )
    reference_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("fodmap_references.id", ondelete="CASCADE"),
        nullable=False,
    )
    mapping_basis: Mapped[str] = mapped_column(String(160), nullable=False)


class RecipeSubstitutionReview(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "recipe_substitution_reviews"
    __table_args__ = (
        UniqueConstraint(
            "family_id",
            "recipe_ingredient_id",
            "proposal_key",
            name="uq_recipe_substitution_reviews_proposal",
        ),
        CheckConstraint(
            "status IN ('proposed','reviewed','rejected')",
            name="ck_recipe_substitution_reviews_status",
        ),
        CheckConstraint(
            "replacement_quantity IS NULL OR replacement_quantity > 0",
            name="ck_recipe_substitution_reviews_quantity",
        ),
        CheckConstraint(
            "(replacement_quantity IS NULL AND replacement_unit IS NULL) OR "
            "(replacement_quantity IS NOT NULL AND replacement_unit IS NOT NULL)",
            name="ck_recipe_substitution_reviews_unit",
        ),
        Index("ix_recipe_substitution_reviews_family", "family_id"),
    )
    family_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("families.id", ondelete="CASCADE"),
        nullable=False,
    )
    recipe_ingredient_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("recipe_ingredients.id", ondelete="CASCADE"),
        nullable=False,
    )
    proposal_key: Mapped[str] = mapped_column(String(100), nullable=False)
    replacement_name: Mapped[str] = mapped_column(String(160), nullable=False)
    replacement_food_item_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("food_items.id", ondelete="SET NULL"),
        nullable=True,
    )
    reference_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("fodmap_references.id", ondelete="SET NULL"),
        nullable=True,
    )
    replacement_quantity: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))
    replacement_unit: Mapped[str | None] = mapped_column(String(24))
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="proposed")
    notes: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
