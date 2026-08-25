from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.food_catalog import Recipe, RecipeIngredient
from app.services.nutrition_learning import (
    IngredientQuantityAnomaly,
    IngredientQuantityObservation,
    detect_quantity_anomalies,
)
from app.services.recipe_evidence_collector import (
    RecipeEvidenceCollection,
    collect_recipe_nutrition_evidence,
)
from app.services.recipe_evidence_search import RecipeEvidenceSearchError

STATUS_NO_INGREDIENTS = "NO_INGREDIENTS"
STATUS_SEARCH_ERROR = "SEARCH_ERROR"
STATUS_QUANTITY_ANOMALY = "QUANTITY_ANOMALY"
STATUS_NO_EVIDENCE = "NO_EVIDENCE"
STATUS_LOW_EVIDENCE = "LOW_EVIDENCE"
STATUS_EVIDENCE_GOOD_SERVINGS_UNKNOWN = "EVIDENCE_GOOD_SERVINGS_UNKNOWN"
STATUS_GOOD = "GOOD"


@dataclass(frozen=True)
class RecipeLearningDiagnostic:
    recipe_name: str
    ingredient_count: int
    serving_count: Decimal | None
    search_hit_count: int
    structured_page_count: int
    failed_page_count: int
    evidence_count: int
    accepted_count: int
    estimate_kcal_per_serving: Decimal | None
    lower_kcal_per_serving: Decimal | None
    upper_kcal_per_serving: Decimal | None
    retained_source_count: int
    mean_similarity: Decimal | None
    confidence: str | None
    anomaly_count: int
    anomalies: tuple[IngredientQuantityAnomaly, ...]
    status: str
    error: str | None = None


@dataclass(frozen=True)
class NutritionLearningDiagnosticReport:
    recipes: tuple[RecipeLearningDiagnostic, ...]

    @property
    def status_counts(self) -> dict[str, int]:
        return dict(Counter(item.status for item in self.recipes))


def classify_recipe_status(
    *,
    ingredient_count: int,
    serving_count: Decimal | None,
    anomaly_count: int,
    collection: RecipeEvidenceCollection | None,
    search_error: str | None = None,
) -> str:
    if ingredient_count == 0:
        return STATUS_NO_INGREDIENTS
    if search_error is not None:
        return STATUS_SEARCH_ERROR
    if anomaly_count > 0:
        return STATUS_QUANTITY_ANOMALY
    if collection is None or collection.estimate is None or not collection.scored:
        return STATUS_NO_EVIDENCE
    if collection.estimate.confidence == "low":
        return STATUS_LOW_EVIDENCE
    if serving_count is None:
        return STATUS_EVIDENCE_GOOD_SERVINGS_UNKNOWN
    return STATUS_GOOD


def _diagnostic_from_collection(
    *,
    recipe: Recipe,
    anomalies: tuple[IngredientQuantityAnomaly, ...],
    collection: RecipeEvidenceCollection | None,
    search_error: str | None = None,
) -> RecipeLearningDiagnostic:
    estimate = collection.estimate if collection is not None else None
    status = classify_recipe_status(
        ingredient_count=len(recipe.ingredients),
        serving_count=recipe.serving_count,
        anomaly_count=len(anomalies),
        collection=collection,
        search_error=search_error,
    )
    return RecipeLearningDiagnostic(
        recipe_name=recipe.name,
        ingredient_count=len(recipe.ingredients),
        serving_count=recipe.serving_count,
        search_hit_count=collection.search_hit_count if collection is not None else 0,
        structured_page_count=(
            collection.structured_page_count if collection is not None else 0
        ),
        failed_page_count=collection.failed_page_count if collection is not None else 0,
        evidence_count=len(collection.evidence) if collection is not None else 0,
        accepted_count=len(collection.scored) if collection is not None else 0,
        estimate_kcal_per_serving=(
            estimate.energy_kcal_per_serving if estimate is not None else None
        ),
        lower_kcal_per_serving=(
            estimate.lower_kcal_per_serving if estimate is not None else None
        ),
        upper_kcal_per_serving=(
            estimate.upper_kcal_per_serving if estimate is not None else None
        ),
        retained_source_count=estimate.retained_count if estimate is not None else 0,
        mean_similarity=estimate.mean_similarity if estimate is not None else None,
        confidence=estimate.confidence if estimate is not None else None,
        anomaly_count=len(anomalies),
        anomalies=anomalies,
        status=status,
        error=search_error,
    )


def _quantity_anomalies_by_recipe(
    recipes: list[Recipe],
) -> dict[str, tuple[IngredientQuantityAnomaly, ...]]:
    observations = [
        IngredientQuantityObservation(
            recipe_name=recipe.name,
            catalog_key=ingredient.food_item.catalog_key,
            ingredient_name=ingredient.food_item.name,
            quantity=ingredient.quantity,
            unit=ingredient.unit,
        )
        for recipe in recipes
        for ingredient in recipe.ingredients
    ]
    grouped: dict[str, list[IngredientQuantityAnomaly]] = {}
    for anomaly in detect_quantity_anomalies(observations):
        grouped.setdefault(anomaly.recipe_name, []).append(anomaly)
    return {name: tuple(items) for name, items in grouped.items()}


def load_legacy_recipes(
    db: Session,
    *,
    recipe_key_prefix: str = "legacy-v1:",
) -> list[Recipe]:
    statement = (
        select(Recipe)
        .options(
            selectinload(Recipe.ingredients).selectinload(RecipeIngredient.food_item)
        )
        .where(
            Recipe.is_active.is_(True),
            Recipe.recipe_key.like(f"{recipe_key_prefix}%"),
        )
        .order_by(Recipe.name)
    )
    return list(db.scalars(statement))


def build_nutrition_learning_diagnostic_report(
    db: Session,
    *,
    max_results: int = 10,
    offset: int = 0,
    limit: int | None = None,
    recipe_key_prefix: str = "legacy-v1:",
    collector: Callable[..., RecipeEvidenceCollection] = (
        collect_recipe_nutrition_evidence
    ),
) -> NutritionLearningDiagnosticReport:
    recipes = load_legacy_recipes(db, recipe_key_prefix=recipe_key_prefix)
    anomalies_by_recipe = _quantity_anomalies_by_recipe(recipes)

    selected = recipes[max(offset, 0) :]
    if limit is not None:
        selected = selected[: max(limit, 0)]

    diagnostics: list[RecipeLearningDiagnostic] = []
    for recipe in selected:
        anomalies = anomalies_by_recipe.get(recipe.name, ())
        if not recipe.ingredients:
            diagnostics.append(
                _diagnostic_from_collection(
                    recipe=recipe,
                    anomalies=anomalies,
                    collection=None,
                )
            )
            continue

        ingredient_names = tuple(
            ingredient.food_item.name for ingredient in recipe.ingredients
        )
        try:
            collection = collector(
                recipe_name=recipe.name,
                ingredient_names=ingredient_names,
                max_results=max_results,
            )
        except RecipeEvidenceSearchError as exc:
            diagnostics.append(
                _diagnostic_from_collection(
                    recipe=recipe,
                    anomalies=anomalies,
                    collection=None,
                    search_error=str(exc),
                )
            )
            continue

        diagnostics.append(
            _diagnostic_from_collection(
                recipe=recipe,
                anomalies=anomalies,
                collection=collection,
            )
        )

    return NutritionLearningDiagnosticReport(recipes=tuple(diagnostics))
