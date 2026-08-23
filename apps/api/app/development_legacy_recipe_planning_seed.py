import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.food_catalog import Recipe, RecipeCompositionSnapshot

STRUCTURE_NAMESPACE = uuid.UUID("2caa981e-63a2-4f3b-b116-8203ae068498")
STRUCTURE_COMPOSITION_VERSION = "legacy-v1-structure-only-v1"
STRUCTURE_CALCULATION_VERSION = "legacy-v1-structure-only-v1"
STRUCTURE_COMPUTED_AT = datetime(2026, 1, 1, tzinfo=UTC)


@dataclass(frozen=True)
class DevelopmentLegacyRecipePlanningSeedResult:
    recipe_count: int


def _composition_id(recipe_id: uuid.UUID) -> uuid.UUID:
    return uuid.uuid5(STRUCTURE_NAMESPACE, f"recipe:{recipe_id}")


def seed_development_legacy_recipe_planning_catalog(
    session: Session,
) -> DevelopmentLegacyRecipePlanningSeedResult:
    recipes = list(
        session.scalars(
            select(Recipe)
            .where(Recipe.source == "legacy-v1", Recipe.is_active.is_(True))
            .order_by(Recipe.recipe_key)
        ).all()
    )
    for recipe in recipes:
        if recipe.suitable_meal_types is None:
            recipe.suitable_meal_types = ["lunch", "dinner"]
        composition_id = _composition_id(recipe.id)
        composition = session.get(RecipeCompositionSnapshot, composition_id)
        if composition is None:
            composition = RecipeCompositionSnapshot(
                id=composition_id,
                recipe_id=recipe.id,
            )
            session.add(composition)
        composition.recipe_id = recipe.id
        composition.reference_quantity = Decimal(1)
        composition.reference_unit = "serving"
        composition.energy_kcal = None
        composition.composition_version = STRUCTURE_COMPOSITION_VERSION
        composition.calculation_version = STRUCTURE_CALCULATION_VERSION
        composition.calculation_inputs = {
            "evidence_level": "structure_only",
            "confidence": "unknown",
            "source": "real NutriFlow v1 recipe structure",
            "warning": (
                "The v1 snapshot does not provide reliable nutrition for this recipe. "
                "The recipe is available for preference-aware planning but must not be "
                "treated as calorie-known until its ingredients are nutritionally enriched."
            ),
        }
        composition.computed_at = STRUCTURE_COMPUTED_AT
    session.flush()
    return DevelopmentLegacyRecipePlanningSeedResult(recipe_count=len(recipes))
