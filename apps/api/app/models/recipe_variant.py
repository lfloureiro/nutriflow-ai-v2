import uuid

from sqlalchemy import JSON, CheckConstraint, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class FamilyRecipeVariant(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "family_recipe_variants"
    __table_args__ = (
        UniqueConstraint("recipe_id", name="uq_family_recipe_variants_recipe"),
        UniqueConstraint("lineage_id", "revision", name="uq_family_recipe_variants_revision"),
        CheckConstraint(
            "status IN ('draft','active','retired')", name="ck_family_recipe_variants_status"
        ),
        CheckConstraint("revision > 0 AND version > 0", name="ck_family_recipe_variants_versions"),
    )
    family_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("families.id", ondelete="CASCADE"), index=True
    )
    base_recipe_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("recipes.id", ondelete="RESTRICT"), index=True
    )
    recipe_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("recipes.id", ondelete="RESTRICT"))
    lineage_id: Mapped[uuid.UUID] = mapped_column(default=uuid.uuid4)
    revision: Mapped[int] = mapped_column(Integer, default=1)
    version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(16), default="draft")
    name: Mapped[str] = mapped_column(String(100))
    base_fingerprint: Mapped[str] = mapped_column(String(64))
    variant_fingerprint: Mapped[str] = mapped_column(String(64))
    operations: Mapped[list[dict]] = mapped_column(JSON)
    activation_evidence: Mapped[dict | None] = mapped_column(JSON)
