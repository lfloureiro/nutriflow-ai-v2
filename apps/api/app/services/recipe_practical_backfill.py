from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.food_catalog import (
    FoodCompositionSnapshot,
    FoodItem,
    Recipe,
    RecipeIngredient,
)
from app.services.recipe_nutrition import build_recipe_composition


@dataclass(frozen=True)
class RecipePracticalBackfillResult:
    recipe_name: str
    energy_kcal: Decimal | None
    energy_per_serving_kcal: Decimal | None
    evidence: str
    confidence: str | None
    serving_count: Decimal | None
    serving_count_estimated: bool
    primary_protein: str | None
    primary_carbohydrate: str | None
    vegetable_level: str
    energy_load_signal: str
    balance_signals: tuple[str, ...]
    issue_count: int


def _recipes(
    db: Session,
    *,
    recipe_key_prefix: str,
) -> list[Recipe]:
    return list(
        db.scalars(
            select(Recipe)
            .options(
                selectinload(Recipe.ingredients)
                .selectinload(RecipeIngredient.food_item)
                .selectinload(FoodItem.compositions)
                .selectinload(FoodCompositionSnapshot.nutrients),
                selectinload(Recipe.compositions),
            )
            .where(
                Recipe.is_active.is_(True),
                Recipe.recipe_key.like(f"{recipe_key_prefix}%"),
            )
            .order_by(Recipe.name, Recipe.id)
        ).all()
    )


def _dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _list_of_strings(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(str(item) for item in value)


def _result(recipe: Recipe) -> RecipePracticalBackfillResult:
    composition = recipe.compositions[-1]
    inputs = _dict(composition.calculation_inputs)
    practical = _dict(inputs.get("practical_profile"))
    practical_energy = _dict(inputs.get("practical_energy"))

    divisor: Decimal | None = recipe.serving_count
    if divisor is None and composition.reference_unit == "serving":
        divisor = composition.reference_quantity
    energy_per_serving = (
        composition.energy_kcal / divisor
        if composition.energy_kcal is not None and divisor is not None
        else None
    )

    if inputs.get("practical_energy_used") is True:
        evidence = "practical_estimate"
        raw_confidence = practical_energy.get("confidence")
        confidence = raw_confidence if isinstance(raw_confidence, str) else "low"
    elif composition.energy_kcal is not None:
        evidence = "ingredient_calculated"
        confidence = "high"
    else:
        evidence = "unavailable"
        confidence = None

    raw_issues = inputs.get("issues")
    issue_count = len(raw_issues) if isinstance(raw_issues, list) else 0

    primary_protein = practical.get("primary_protein")
    primary_carbohydrate = practical.get("primary_carbohydrate")
    vegetable_level = practical.get("vegetable_level")
    energy_load_signal = practical.get("energy_load_signal")

    return RecipePracticalBackfillResult(
        recipe_name=recipe.name,
        energy_kcal=composition.energy_kcal,
        energy_per_serving_kcal=energy_per_serving,
        evidence=evidence,
        confidence=confidence,
        serving_count=divisor,
        serving_count_estimated=inputs.get("serving_count_estimated") is True,
        primary_protein=(
            primary_protein if isinstance(primary_protein, str) else None
        ),
        primary_carbohydrate=(
            primary_carbohydrate if isinstance(primary_carbohydrate, str) else None
        ),
        vegetable_level=(
            vegetable_level if isinstance(vegetable_level, str) else "unknown"
        ),
        energy_load_signal=(
            energy_load_signal if isinstance(energy_load_signal, str) else "unknown"
        ),
        balance_signals=_list_of_strings(practical.get("balance_signals")),
        issue_count=issue_count,
    )


def backfill_recipe_practical_nutrition(
    db: Session,
    *,
    recipe_key_prefix: str = "legacy-v1:",
    commit: bool = True,
) -> tuple[RecipePracticalBackfillResult, ...]:
    recipes = _recipes(db, recipe_key_prefix=recipe_key_prefix)
    for recipe in recipes:
        build_recipe_composition(recipe)
    db.flush()
    results = tuple(_result(recipe) for recipe in recipes)
    if commit:
        db.commit()
    else:
        db.rollback()
    return results
