import re
import unicodedata
from dataclasses import dataclass
from decimal import Decimal
from difflib import SequenceMatcher

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.food_catalog import Recipe, RecipeCompositionSnapshot
from app.schemas.external_menu import ExternalMenuNutrientWrite, ExternalMenuNutritionWrite
from app.services.recipe_nutrition import CALCULATION_VERSION
from app.services.restaurant_menu_scraper import ScrapedMenuItem

MIN_ESTIMATE_SCORE = Decimal("0.900")
MIN_ESTIMATE_MARGIN = Decimal("0.050")


@dataclass(frozen=True)
class RestaurantDishNutritionEstimate:
    nutrition: ExternalMenuNutritionWrite
    recipe_key: str
    recipe_name: str
    score: Decimal


def _normalize(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.casefold())
    ascii_text = "".join(
        character for character in normalized if not unicodedata.combining(character)
    )
    return " ".join(re.findall(r"[a-z0-9]+", ascii_text))


def _similarity(item: ScrapedMenuItem, recipe: Recipe) -> Decimal:
    item_name = _normalize(item.name)
    recipe_name = _normalize(recipe.name)
    if item_name == recipe_name:
        return Decimal("0.980")
    name_score = Decimal(str(SequenceMatcher(None, item_name, recipe_name).ratio()))
    if item.description and recipe.description:
        description_score = Decimal(
            str(
                SequenceMatcher(
                    None,
                    _normalize(item.description),
                    _normalize(recipe.description),
                ).ratio()
            )
        )
        name_score = max(
            name_score,
            name_score * Decimal("0.8") + description_score * Decimal("0.2"),
        )
    return name_score.quantize(Decimal("0.001"))


def _trusted_composition(composition: RecipeCompositionSnapshot) -> bool:
    if composition.energy_kcal is None or composition.calculation_version != CALCULATION_VERSION:
        return False
    inputs = composition.calculation_inputs
    return not (isinstance(inputs, dict) and inputs.get("energy_estimated") is True)


def _latest_trusted_recipes(
    db: Session,
    family_id,
) -> list[tuple[Recipe, RecipeCompositionSnapshot]]:
    recipes = db.scalars(
        select(Recipe)
        .options(
            selectinload(Recipe.compositions).selectinload(RecipeCompositionSnapshot.nutrients)
        )
        .where(
            Recipe.is_active.is_(True),
            or_(Recipe.family_id.is_(None), Recipe.family_id == family_id),
        )
        .order_by(Recipe.name, Recipe.id)
    ).all()
    result: list[tuple[Recipe, RecipeCompositionSnapshot]] = []
    for recipe in recipes:
        trusted = [
            composition
            for composition in recipe.compositions
            if _trusted_composition(composition)
        ]
        if not trusted or recipe.serving_count is None or recipe.serving_count <= 0:
            continue
        result.append((recipe, trusted[-1]))
    return result


def estimate_restaurant_dish_nutrition(
    db: Session,
    *,
    family_id,
    item: ScrapedMenuItem,
) -> RestaurantDishNutritionEstimate | None:
    ranked = sorted(
        (
            (_similarity(item, recipe), recipe, composition)
            for recipe, composition in _latest_trusted_recipes(db, family_id)
        ),
        key=lambda value: (value[0], value[1].name.casefold()),
        reverse=True,
    )
    if not ranked or ranked[0][0] < MIN_ESTIMATE_SCORE:
        return None
    if len(ranked) > 1 and ranked[0][0] - ranked[1][0] < MIN_ESTIMATE_MARGIN:
        return None

    score, recipe, composition = ranked[0]
    serving_count = recipe.serving_count
    if serving_count is None or serving_count <= 0 or composition.energy_kcal is None:
        return None
    basis_reference = f"nutriflow-recipe:{recipe.recipe_key}:{composition.id}"
    nutrition = ExternalMenuNutritionWrite(
        evidence_level="estimated",
        confidence=score,
        basis_reference=basis_reference,
        reference_quantity=Decimal(1),
        reference_unit="serving",
        energy_kcal=composition.energy_kcal / serving_count,
        nutrients=[
            ExternalMenuNutrientWrite(
                key=nutrient.nutrient_key,
                value=nutrient.value / serving_count,
                unit=nutrient.unit,
            )
            for nutrient in composition.nutrients
        ],
    )
    return RestaurantDishNutritionEstimate(
        nutrition=nutrition,
        recipe_key=recipe.recipe_key,
        recipe_name=recipe.name,
        score=score,
    )
