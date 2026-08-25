import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.food_catalog import (
    FoodCompositionSnapshot,
    FoodItem,
    FoodNutrientComponent,
    Recipe,
    RecipeIngredient,
)
from app.services.portfir import PortfirFoodNutrition
from app.services.portfir_matching import (
    PortfirMatch,
    automatic_portfir_match,
    rank_portfir_matches,
)
from app.services.recipe_nutrition import build_recipe_composition


class PortfirEnrichmentError(ValueError):
    pass


@dataclass(frozen=True)
class PortfirEnrichmentResult:
    ingredient_id: uuid.UUID
    catalog_key: str
    composition_id: uuid.UUID
    data_version: str
    created: bool
    recalculated_recipe_ids: tuple[uuid.UUID, ...]


@dataclass(frozen=True)
class PortfirAutoEnrichmentItem:
    catalog_key: str
    name: str
    status: str
    matched_code: str | None
    matched_name: str | None
    confidence: Decimal | None
    reason: str | None
    composition_created: bool
    recalculated_recipe_count: int


def _shared_ingredient(db: Session, catalog_key: str) -> FoodItem:
    item = db.scalar(
        select(FoodItem)
        .options(
            selectinload(FoodItem.compositions).selectinload(
                FoodCompositionSnapshot.nutrients
            )
        )
        .where(
            FoodItem.catalog_key == catalog_key,
            FoodItem.family_id.is_(None),
            FoodItem.food_kind == "ingredient",
            FoodItem.is_active.is_(True),
        )
    )
    if item is None:
        raise PortfirEnrichmentError(f"Shared ingredient {catalog_key!r} was not found.")
    return item


def _recipes_using_ingredient(db: Session, ingredient_id: uuid.UUID) -> list[Recipe]:
    return list(
        db.scalars(
            select(Recipe)
            .join(RecipeIngredient)
            .options(
                selectinload(Recipe.ingredients)
                .selectinload(RecipeIngredient.food_item)
                .selectinload(FoodItem.compositions)
                .selectinload(FoodCompositionSnapshot.nutrients),
                selectinload(Recipe.compositions),
            )
            .where(
                RecipeIngredient.food_item_id == ingredient_id,
                Recipe.is_active.is_(True),
            )
        )
        .unique()
        .all()
    )


def _data_version(food: PortfirFoodNutrition) -> str:
    safe_code = "".join(
        character
        for character in food.code
        if character.isalnum() or character in "-_"
    )
    return (
        f"portfir-{food.version}-{safe_code or 'unknown'}-{food.reference_unit}"
    )[:64]


def apply_portfir_nutrition_to_shared_ingredient(
    db: Session,
    *,
    catalog_key: str,
    food: PortfirFoodNutrition,
    match: PortfirMatch | None = None,
    effective_at: datetime | None = None,
) -> PortfirEnrichmentResult:
    item = _shared_ingredient(db, catalog_key)
    data_version = _data_version(food)
    existing = next(
        (
            composition
            for composition in item.compositions
            if composition.data_version == data_version
        ),
        None,
    )
    if existing is not None:
        return PortfirEnrichmentResult(
            ingredient_id=item.id,
            catalog_key=item.catalog_key,
            composition_id=existing.id,
            data_version=data_version,
            created=False,
            recalculated_recipe_ids=(),
        )

    notes: dict[str, object] = {
        "portfir_code": food.code,
        "portfir_name": food.name,
        "portfir_version": food.version,
        "reference_basis": f"100 {food.reference_unit}",
        "curation": "automatic-high-confidence" if match is not None else "explicit-match",
    }
    if match is not None:
        notes["match"] = {
            "score": str(match.score),
            "reason": match.reason,
            "normalized_query": match.normalized_query,
            "normalized_candidate": match.normalized_candidate,
        }

    composition = FoodCompositionSnapshot(
        reference_quantity=Decimal(100),
        reference_unit=food.reference_unit,
        energy_kcal=food.energy_kcal,
        data_version=data_version,
        source="portfir",
        source_reference=food.source_reference,
        effective_at=effective_at or datetime.now(UTC),
        notes=json.dumps(notes, ensure_ascii=False, sort_keys=True),
    )
    composition.nutrients.extend(
        FoodNutrientComponent(
            nutrient_key=nutrient.key,
            value=nutrient.value,
            unit=nutrient.unit,
        )
        for nutrient in food.nutrients
    )
    item.compositions.append(composition)
    db.flush()

    recipes = _recipes_using_ingredient(db, item.id)
    for recipe in recipes:
        build_recipe_composition(recipe)
    db.flush()
    return PortfirEnrichmentResult(
        ingredient_id=item.id,
        catalog_key=item.catalog_key,
        composition_id=composition.id,
        data_version=data_version,
        created=True,
        recalculated_recipe_ids=tuple(recipe.id for recipe in recipes),
    )


def _missing_shared_ingredients(db: Session, *, limit: int) -> list[FoodItem]:
    items = list(
        db.scalars(
            select(FoodItem)
            .options(selectinload(FoodItem.compositions))
            .where(
                FoodItem.family_id.is_(None),
                FoodItem.food_kind == "ingredient",
                FoodItem.is_active.is_(True),
            )
            .order_by(FoodItem.name, FoodItem.id)
        ).all()
    )
    missing: list[FoodItem] = []
    for item in items:
        if any(composition.energy_kcal is not None for composition in item.compositions):
            continue
        missing.append(item)
        if len(missing) >= limit:
            break
    return missing


def auto_enrich_shared_ingredients_from_portfir(
    db: Session,
    *,
    foods: tuple[PortfirFoodNutrition, ...],
    apply: bool,
    limit: int = 200,
) -> tuple[PortfirAutoEnrichmentItem, ...]:
    result: list[PortfirAutoEnrichmentItem] = []
    for item in _missing_shared_ingredients(db, limit=limit):
        automatic = automatic_portfir_match(item.name, foods)
        if automatic is None:
            ranked = rank_portfir_matches(item.name, foods, limit=1)
            suggestion = ranked[0] if ranked else None
            result.append(
                PortfirAutoEnrichmentItem(
                    catalog_key=item.catalog_key,
                    name=item.name,
                    status="review" if suggestion is not None else "unmatched",
                    matched_code=None if suggestion is None else suggestion.food.code,
                    matched_name=None if suggestion is None else suggestion.food.name,
                    confidence=None if suggestion is None else suggestion.score,
                    reason=None if suggestion is None else suggestion.reason,
                    composition_created=False,
                    recalculated_recipe_count=0,
                )
            )
            continue

        enrichment: PortfirEnrichmentResult | None = None
        if apply:
            enrichment = apply_portfir_nutrition_to_shared_ingredient(
                db,
                catalog_key=item.catalog_key,
                food=automatic.food,
                match=automatic,
            )
        result.append(
            PortfirAutoEnrichmentItem(
                catalog_key=item.catalog_key,
                name=item.name,
                status="applied" if apply else "auto_match",
                matched_code=automatic.food.code,
                matched_name=automatic.food.name,
                confidence=automatic.score,
                reason=automatic.reason,
                composition_created=enrichment.created if enrichment is not None else False,
                recalculated_recipe_count=(
                    len(enrichment.recalculated_recipe_ids)
                    if enrichment is not None
                    else 0
                ),
            )
        )
    return tuple(result)