"""add food item classifications

Revision ID: f1a7c3e9b2d6
Revises: e3f7a2b6c1d9
Create Date: 2026-09-20
"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f1a7c3e9b2d6"
down_revision: str | Sequence[str] | None = "e3f7a2b6c1d9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_CLASSIFICATION_NAMESPACE = uuid.UUID("2f634485-9a2e-42ec-98d2-e15bdeddd6c3")
_SOURCE = "legacy-v1-curated"
_SOURCE_REFERENCE = "nutriflow-v1-loureiro-food-classification-v1"

# Explicit catalogue metadata. Runtime matching never infers these values from names.
_LEGACY_CLASSIFICATIONS: dict[str, tuple[str, ...]] = {
    "legacy-v1:ingredient:1": ("simple_sugars",),
    "legacy-v1:ingredient:15": ("processed_meat",),
    "legacy-v1:ingredient:35": ("alcohol",),
    "legacy-v1:ingredient:36": ("processed_meat",),
    "legacy-v1:ingredient:54": ("gluten", "refined_grains"),
    "legacy-v1:ingredient:58": ("gluten", "refined_flour", "refined_grains"),
    "legacy-v1:ingredient:61": ("gluten", "refined_grains"),
    "legacy-v1:ingredient:62": ("processed_meat",),
    "legacy-v1:ingredient:63": ("processed_meat",),
    "legacy-v1:ingredient:76": ("processed_meat",),
    "legacy-v1:ingredient:80": ("gluten", "refined_grains"),
    "legacy-v1:ingredient:81": ("gluten", "refined_grains"),
    "legacy-v1:ingredient:85": ("gluten", "refined_grains"),
    "legacy-v1:ingredient:87": ("gluten", "refined_grains"),
    "legacy-v1:ingredient:91": ("soy",),
    "legacy-v1:ingredient:99": ("gluten", "refined_grains"),
    "legacy-v1:ingredient:106": ("processed_meat",),
    "legacy-v1:ingredient:134": ("processed_meat",),
    "legacy-v1:ingredient:148": ("alcohol",),
    "legacy-v1:ingredient:149": ("alcohol",),
    "legacy-v1:ingredient:150": ("alcohol",),
}


def _classification_id(
    catalog_key: str,
    classification_type: str,
    classification_key: str,
) -> uuid.UUID:
    return uuid.uuid5(
        _CLASSIFICATION_NAMESPACE,
        f"{catalog_key}:{classification_type}:{classification_key}",
    )


def upgrade() -> None:
    op.create_table(
        "food_item_classifications",
        sa.Column("food_item_id", sa.Uuid(), nullable=False),
        sa.Column("classification_type", sa.String(length=48), nullable=False),
        sa.Column("classification_key", sa.String(length=120), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("source_reference", sa.String(length=255), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "length(classification_type) > 0",
            name="ck_food_item_classifications_type_nonempty",
        ),
        sa.CheckConstraint(
            "length(classification_key) > 0",
            name="ck_food_item_classifications_key_nonempty",
        ),
        sa.ForeignKeyConstraint(
            ["food_item_id"],
            ["food_items.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "food_item_id",
            "classification_type",
            "classification_key",
            name="uq_food_item_classifications_identity",
        ),
    )
    op.create_index(
        "ix_food_item_classifications_lookup",
        "food_item_classifications",
        ["classification_type", "classification_key"],
        unique=False,
    )

    connection = op.get_bind()
    keys = tuple(_LEGACY_CLASSIFICATIONS)
    if not keys:
        return
    food_items = sa.table(
        "food_items",
        sa.column("id", sa.Uuid()),
        sa.column("catalog_key", sa.String()),
    )
    existing = connection.execute(
        sa.select(food_items.c.id, food_items.c.catalog_key).where(
            food_items.c.catalog_key.in_(keys)
        )
    ).all()
    by_key = {row.catalog_key: row.id for row in existing}

    rows: list[dict[str, object]] = []
    for catalog_key, classification_keys in _LEGACY_CLASSIFICATIONS.items():
        food_item_id = by_key.get(catalog_key)
        if food_item_id is None:
            continue
        for classification_key in classification_keys:
            rows.append(
                {
                    "id": _classification_id(
                        catalog_key,
                        "food_category",
                        classification_key,
                    ),
                    "food_item_id": food_item_id,
                    "classification_type": "food_category",
                    "classification_key": classification_key,
                    "source": _SOURCE,
                    "source_reference": _SOURCE_REFERENCE,
                }
            )
    if rows:
        classifications = sa.table(
            "food_item_classifications",
            sa.column("id", sa.Uuid()),
            sa.column("food_item_id", sa.Uuid()),
            sa.column("classification_type", sa.String()),
            sa.column("classification_key", sa.String()),
            sa.column("source", sa.String()),
            sa.column("source_reference", sa.String()),
        )
        op.bulk_insert(classifications, rows)


def downgrade() -> None:
    op.drop_index(
        "ix_food_item_classifications_lookup",
        table_name="food_item_classifications",
    )
    op.drop_table("food_item_classifications")
