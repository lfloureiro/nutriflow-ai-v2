import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.food_catalog import FoodItem, FoodItemClassification

CLASSIFICATION_NAMESPACE = uuid.UUID("2f634485-9a2e-42ec-98d2-e15bdeddd6c3")
CLASSIFICATION_SOURCE = "legacy-v1-curated"
CLASSIFICATION_SOURCE_REFERENCE = "nutriflow-v1-loureiro-food-classification-v1"

# Explicit catalogue metadata keyed by stable legacy catalogue identifiers.
# These values must never be reconstructed from FoodItem names at runtime.
LEGACY_FOOD_CATEGORY_CLASSIFICATIONS: dict[str, tuple[str, ...]] = {
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


@dataclass(frozen=True)
class DevelopmentFoodClassificationSeedResult:
    classification_count: int
    classified_item_count: int


def _classification_id(
    catalog_key: str,
    classification_type: str,
    classification_key: str,
) -> uuid.UUID:
    return uuid.uuid5(
        CLASSIFICATION_NAMESPACE,
        f"{catalog_key}:{classification_type}:{classification_key}",
    )


def seed_development_food_classifications(
    session: Session,
) -> DevelopmentFoodClassificationSeedResult:
    keys = tuple(LEGACY_FOOD_CATEGORY_CLASSIFICATIONS)
    items = {
        item.catalog_key: item
        for item in session.scalars(
            select(FoodItem).where(FoodItem.catalog_key.in_(keys))
        ).all()
    }

    classification_count = 0
    classified_item_count = 0
    for catalog_key, classification_keys in LEGACY_FOOD_CATEGORY_CLASSIFICATIONS.items():
        item = items.get(catalog_key)
        if item is None:
            continue
        classified_item_count += 1
        for classification_key in classification_keys:
            classification_id = _classification_id(
                catalog_key,
                "food_category",
                classification_key,
            )
            classification = session.get(FoodItemClassification, classification_id)
            if classification is None:
                classification = FoodItemClassification(id=classification_id)
                session.add(classification)
            classification.food_item_id = item.id
            classification.classification_type = "food_category"
            classification.classification_key = classification_key
            classification.source = CLASSIFICATION_SOURCE
            classification.source_reference = CLASSIFICATION_SOURCE_REFERENCE
            classification_count += 1

    session.flush()
    return DevelopmentFoodClassificationSeedResult(
        classification_count=classification_count,
        classified_item_count=classified_item_count,
    )
