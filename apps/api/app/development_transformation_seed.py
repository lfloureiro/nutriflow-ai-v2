import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.family import Family
from app.models.food_catalog import FoodCompositionSnapshot, FoodItem, FoodNutrientComponent
from app.models.food_transformation_profile import FoodTransformationProfile

TRANSFORMATION_NAMESPACE = uuid.UUID("bc4d1608-fda3-477a-a402-49809b588c9d")
TRANSFORMATION_SOURCE = "development-transformation"
TRANSFORMATION_REFERENCE = "nutriflow-v2-development-transformations-v1"
TRANSFORMATION_DATA_VERSION = "development-transformation-v1"
TRANSFORMATION_EFFECTIVE_AT = datetime(2026, 9, 16, 12, 0, tzinfo=UTC)


@dataclass(frozen=True)
class TransformationFoodDefinition:
    catalog_key: str
    substitution_group: str
    typical_quantity: Decimal
    typical_unit: str
    energy_kcal: Decimal
    protein_g: Decimal
    fiber_g: Decimal
    sodium_mg: Decimal


@dataclass(frozen=True)
class DevelopmentTransformationSeedResult:
    profile_count: int
    composition_count: int


DEFINITIONS = (
    TransformationFoodDefinition(
        catalog_key="breakfast:ingredient:natural-yogurt",
        substitution_group="cultured-dairy-yogurt",
        typical_quantity=Decimal(170),
        typical_unit="g",
        energy_kcal=Decimal(105),
        protein_g=Decimal("6.5"),
        fiber_g=Decimal(0),
        sodium_mg=Decimal(85),
    ),
    TransformationFoodDefinition(
        catalog_key="breakfast:ingredient:greek-yogurt",
        substitution_group="cultured-dairy-yogurt",
        typical_quantity=Decimal(170),
        typical_unit="g",
        energy_kcal=Decimal(135),
        protein_g=Decimal(17),
        fiber_g=Decimal(0),
        sodium_mg=Decimal(70),
    ),
)


def _stable_id(kind: str, key: str) -> uuid.UUID:
    return uuid.uuid5(TRANSFORMATION_NAMESPACE, f"{kind}:{key}")


def _food(session: Session, catalog_key: str) -> FoodItem:
    item = session.scalar(select(FoodItem).where(FoodItem.catalog_key == catalog_key))
    if item is None:
        raise RuntimeError(
            f"Development transformation seed requires catalogue item {catalog_key!r}."
        )
    return item


def _ensure_composition(
    session: Session,
    item: FoodItem,
    definition: TransformationFoodDefinition,
) -> None:
    composition_id = _stable_id("composition", definition.catalog_key)
    composition = session.get(FoodCompositionSnapshot, composition_id)
    if composition is None:
        composition = FoodCompositionSnapshot(id=composition_id, food_item_id=item.id)
        session.add(composition)
    composition.food_item_id = item.id
    composition.reference_quantity = definition.typical_quantity
    composition.reference_unit = definition.typical_unit
    composition.energy_kcal = definition.energy_kcal
    composition.data_version = TRANSFORMATION_DATA_VERSION
    composition.source = TRANSFORMATION_SOURCE
    composition.source_reference = TRANSFORMATION_REFERENCE
    composition.effective_at = TRANSFORMATION_EFFECTIVE_AT
    composition.notes = (
        "Synthetic development evidence used only to exercise structured meal transformations."
    )
    session.flush()

    values = {
        "protein": (definition.protein_g, "g"),
        "fiber": (definition.fiber_g, "g"),
        "sodium": (definition.sodium_mg, "mg"),
    }
    existing = {component.nutrient_key: component for component in composition.nutrients}
    for nutrient_key, (value, unit) in values.items():
        component = existing.get(nutrient_key)
        if component is None:
            component = FoodNutrientComponent(
                id=_stable_id("nutrient", f"{definition.catalog_key}:{nutrient_key}"),
                composition_snapshot_id=composition.id,
                nutrient_key=nutrient_key,
                value=value,
                unit=unit,
            )
            session.add(component)
        else:
            component.value = value
            component.unit = unit
    session.flush()


def seed_development_transformations(
    session: Session,
    *,
    families: tuple[Family, ...],
) -> DevelopmentTransformationSeedResult:
    items = {
        definition.catalog_key: _food(session, definition.catalog_key)
        for definition in DEFINITIONS
    }
    for definition in DEFINITIONS:
        _ensure_composition(session, items[definition.catalog_key], definition)

    profile_count = 0
    for family in families:
        for definition in DEFINITIONS:
            item = items[definition.catalog_key]
            profile_id = _stable_id("profile", f"{family.id}:{definition.catalog_key}")
            profile = session.get(FoodTransformationProfile, profile_id)
            if profile is None:
                profile = FoodTransformationProfile(id=profile_id, family_id=family.id)
                session.add(profile)
            profile.family_id = family.id
            profile.food_item_id = item.id
            profile.substitution_group = definition.substitution_group
            profile.typical_quantity = definition.typical_quantity
            profile.typical_unit = definition.typical_unit
            profile.auto_transform_enabled = True
            profile.source = TRANSFORMATION_SOURCE
            profile.source_reference = TRANSFORMATION_REFERENCE
            profile_count += 1
    session.flush()

    return DevelopmentTransformationSeedResult(
        profile_count=profile_count,
        composition_count=len(DEFINITIONS),
    )
