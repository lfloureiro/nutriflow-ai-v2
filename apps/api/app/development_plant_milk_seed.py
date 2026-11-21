"""Idempotent development catalogue of milk substitutions.

Retailer examples are discovery leads, not verified per-brand composition.
Generic nutrient numbers below are explicitly provisional illustrative inputs.
Never mark a product as Monash-certified or universally FODMAP safe.
"""
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.family import Family
from app.models.food_catalog import (
    FoodCompositionSnapshot,
    FoodItem,
    FoodNutrientComponent,
)
from app.models.food_transformation_profile import FoodTransformationProfile

NAMESPACE = uuid.UUID("da6b6d59-e026-43d8-a4dd-7aa4ac3a5761")
SOURCE = "development-plant-milk"
SOURCE_REF = "pt-retail-beverage-research-2026-11-21"
VERSION = "development-plant-milk-estimate-v1"
EFFECTIVE = datetime(2026, 11, 20, 12, 0, tzinfo=UTC)
GROUP = "milk-for-breakfast"


@dataclass(frozen=True)
class MilkOption:
    key: str
    name: str
    energy: str
    protein: str
    fiber: str
    sodium: str
    auto: bool
    retail_url: str


OPTIONS = (
    # Existing seed ingredient: same FoodItem, no duplicate dairy item.
    MilkOption("breakfast:ingredient:milk", "Leite meio-gordo", "47", "3.4", "0", "44",
               True, ""),
    MilkOption("plant-milk:rice", "Bebida vegetal de arroz sem adição de açúcar",
               "49", "0.2", "0.2", "30", True,
               "https://www.continente.pt/supermercado/laticinios-e-ovos/bebidas-vegetais-e-vegegurtes/bebida-arroz/"),
    MilkOption("plant-milk:lactose-free", "Leite meio-gordo sem lactose",
               "47", "3.4", "0", "44", True, ""),
    MilkOption("plant-milk:oat", "Bebida vegetal de aveia sem adição de açúcar",
               "43", "1.0", "0.8", "40", False,
               "https://www.continente.pt/produto/bebida-vegetal-de-aveia-sem-acucar-alpro-8152828.html"),
    MilkOption("plant-milk:coconut-rice", "Bebida vegetal de arroz e coco",
               "42", "0.3", "0.2", "30", False,
               "https://www.auchan.pt/pt/alimentacao/produtos-lacteos/bebidas-vegetais/arroz/bebida-arroz-coco-auchan-sem-adicao-de-acucares-sem-gluten-1l/3656235.html"),
)


def _id(kind: str, key: str) -> uuid.UUID:
    return uuid.uuid5(NAMESPACE, f"{kind}:{key}")


def seed_development_plant_milk_options(
    session: Session, *, families: tuple[Family, ...]
) -> tuple[int, int]:
    """Build generic alternatives + comparable profiles. Does not commit.

    Oat/coconut variants remain registered but excluded from automatic swaps
    until serving-size and ingredient-level evidence is verified.
    """
    for option in OPTIONS:
        item = session.scalar(select(FoodItem).where(FoodItem.catalog_key == option.key))
        if item is None:
            item = FoodItem(id=_id("food", option.key), catalog_key=option.key)
            session.add(item)
        # Do not rewrite the name or provenance of the existing milk ingredient.
        if option.key != "breakfast:ingredient:milk":
            item.family_id = None
            item.name = option.name
            item.food_kind = "ingredient"
            item.source = SOURCE
            item.source_reference = option.retail_url or SOURCE_REF
            item.is_active = True
        session.flush()

        composition_id = _id("composition", option.key)
        snapshot = session.get(FoodCompositionSnapshot, composition_id)
        if snapshot is None:
            snapshot = FoodCompositionSnapshot(id=composition_id, food_item_id=item.id)
            session.add(snapshot)
        snapshot.food_item_id = item.id
        snapshot.reference_quantity = Decimal(100)
        snapshot.reference_unit = "ml"
        snapshot.energy_kcal = Decimal(option.energy)
        snapshot.data_version = VERSION
        snapshot.source = SOURCE
        snapshot.source_reference = SOURCE_REF
        snapshot.effective_at = EFFECTIVE
        snapshot.notes = (
            "Generic illustrative estimate per 100 ml, not a verified retailer label, "
            "not a clinical/FODMAP approval. Verify brand, additives and serving size."
        )
        session.flush()
        for nutrient, value, unit in (
            ("protein", option.protein, "g"),
            ("fiber", option.fiber, "g"),
            ("sodium", option.sodium, "mg"),
        ):
            nutrient_id = _id("nutrient", f"{option.key}:{nutrient}")
            component = session.get(FoodNutrientComponent, nutrient_id)
            if component is None:
                component = FoodNutrientComponent(
                    id=nutrient_id, composition_snapshot_id=snapshot.id,
                    nutrient_key=nutrient,
                )
                session.add(component)
            component.composition_snapshot_id = snapshot.id
            component.value = Decimal(value)
            component.unit = unit
        for family in families:
            profile_id = _id("profile", f"{family.id}:{option.key}")
            profile = session.get(FoodTransformationProfile, profile_id)
            if profile is None:
                profile = FoodTransformationProfile(id=profile_id, family_id=family.id)
                session.add(profile)
            profile.family_id = family.id
            profile.food_item_id = item.id
            profile.substitution_group = GROUP
            profile.typical_quantity = Decimal(200)
            profile.typical_unit = "ml"
            profile.auto_transform_enabled = option.auto
            profile.source = SOURCE
            profile.source_reference = SOURCE_REF
    session.flush()
    return len(OPTIONS), sum(option.auto for option in OPTIONS) - 1
