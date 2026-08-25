from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.food_catalog import FoodItem, Recipe, RecipeIngredient


@dataclass(frozen=True)
class LegacyV1UnitCorrection:
    recipe_key: str
    ingredient_catalog_key: str
    quantity: Decimal
    imported_unit: str
    corrected_unit: str
    reason: str


@dataclass(frozen=True)
class LegacyV1UnitCorrectionResult:
    corrected_count: int


# These are corrections to concrete rows in the pinned v1 snapshot, not generic
# assumptions. The original data contains clear unit-shape anomalies: wine with
# a 100/300 quantity encoded as null/g and bacon encoded as ml.
_CORRECTIONS = (
    LegacyV1UnitCorrection(
        recipe_key="legacy-v1:recipe:15",
        ingredient_catalog_key="legacy-v1:ingredient:148",
        quantity=Decimal(100),
        imported_unit="un",
        corrected_unit="ml",
        reason="v1 snapshot stores 100 of white wine with a null unit",
    ),
    LegacyV1UnitCorrection(
        recipe_key="legacy-v1:recipe:30",
        ingredient_catalog_key="legacy-v1:ingredient:150",
        quantity=Decimal(300),
        imported_unit="g",
        corrected_unit="ml",
        reason="v1 snapshot stores 300 of red wine as grams",
    ),
    LegacyV1UnitCorrection(
        recipe_key="legacy-v1:recipe:36",
        ingredient_catalog_key="legacy-v1:ingredient:15",
        quantity=Decimal(50),
        imported_unit="ml",
        corrected_unit="g",
        reason="v1 snapshot stores 50 of bacon pieces as millilitres",
    ),
)


def apply_verified_legacy_v1_unit_corrections(
    db: Session,
) -> LegacyV1UnitCorrectionResult:
    corrected_count = 0
    for correction in _CORRECTIONS:
        row = db.scalar(
            select(RecipeIngredient)
            .join(Recipe, Recipe.id == RecipeIngredient.recipe_id)
            .join(FoodItem, FoodItem.id == RecipeIngredient.food_item_id)
            .where(
                Recipe.recipe_key == correction.recipe_key,
                FoodItem.catalog_key == correction.ingredient_catalog_key,
                RecipeIngredient.quantity == correction.quantity,
                RecipeIngredient.unit == correction.imported_unit,
            )
        )
        if row is None:
            continue
        row.unit = correction.corrected_unit
        provenance = (
            "Correção automática de anomalia verificada no snapshot v1: "
            f"{correction.reason}."
        )
        row.notes = f"{row.notes} {provenance}" if row.notes else provenance
        corrected_count += 1
    if corrected_count:
        db.flush()
    return LegacyV1UnitCorrectionResult(corrected_count=corrected_count)
