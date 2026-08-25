import threading
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy.orm import Session

from app.schemas.nutrition_enrichment import (
    NutritionEnrichmentItemRead,
    NutritionEnrichmentRunRead,
)
from app.services.automatic_unit_conversions import auto_enrich_shared_unit_conversions
from app.services.portfir import (
    PORTFIR_VERSION,
    download_portfir_workbook,
    load_portfir_foods,
)
from app.services.portfir_enrichment import auto_enrich_shared_ingredients_from_portfir
from app.services.recipe_nutrition_reconciliation import (
    reconcile_legacy_recipe_nutrition,
)

DEFAULT_PORTFIR_CACHE_PATH = Path(".cache/portfir/insa_tca.xlsx")
PORTFIR_CACHE_MAX_AGE = timedelta(days=30)
_CACHE_LOCK = threading.Lock()
_RUN_LOCK = threading.Lock()


def _cache_is_fresh(path: Path, *, now: datetime) -> bool:
    if not path.is_file():
        return False
    try:
        modified = datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)
    except OSError:
        return False
    return now - modified <= PORTFIR_CACHE_MAX_AGE


def ensure_portfir_cache(
    *,
    path: Path = DEFAULT_PORTFIR_CACHE_PATH,
    refresh: bool = False,
    now: datetime | None = None,
) -> tuple[Path, bool]:
    observed_at = now or datetime.now(UTC)
    if not refresh and _cache_is_fresh(path, now=observed_at):
        return path, False

    with _CACHE_LOCK:
        if not refresh and _cache_is_fresh(path, now=observed_at):
            return path, False
        download_portfir_workbook(path)
        return path, True


def run_automatic_nutrition_enrichment(
    db: Session,
    *,
    refresh: bool = False,
    limit: int = 200,
    cache_path: Path = DEFAULT_PORTFIR_CACHE_PATH,
) -> NutritionEnrichmentRunRead:
    if limit < 1 or limit > 1000:
        raise ValueError("Nutrition enrichment limit must be between 1 and 1000.")

    with _RUN_LOCK:
        path, cache_refreshed = ensure_portfir_cache(
            path=cache_path,
            refresh=refresh,
        )
        foods = load_portfir_foods(path)

        enrichment = auto_enrich_shared_ingredients_from_portfir(
            db,
            foods=foods,
            apply=True,
            limit=limit,
        )
        conversions = auto_enrich_shared_unit_conversions(db)
        coverage = reconcile_legacy_recipe_nutrition(db)
        items = [
            NutritionEnrichmentItemRead(
                catalog_key=item.catalog_key,
                name=item.name,
                status=item.status,
                matched_code=item.matched_code,
                matched_name=item.matched_name,
                confidence=item.confidence,
                reason=item.reason,
                composition_created=item.composition_created,
                recalculated_recipe_count=item.recalculated_recipe_count,
            )
            for item in enrichment
        ]
        return NutritionEnrichmentRunRead(
            source="portfir",
            source_version=PORTFIR_VERSION,
            cache_refreshed=cache_refreshed,
            applied_count=sum(item.status == "applied" for item in enrichment),
            unit_conversion_count=sum(item.created for item in conversions),
            review_count=sum(item.status == "review" for item in enrichment),
            unmatched_count=sum(item.status == "unmatched" for item in enrichment),
            recalculated_recipe_count=(
                sum(item.recalculated_recipe_count for item in enrichment)
                + sum(item.recalculated_recipe_count for item in conversions)
                + coverage.rebuilt_count
            ),
            legacy_recipe_total_count=coverage.total_count,
            legacy_recipe_rebuilt_count=coverage.rebuilt_count,
            legacy_recipe_calculated_count=coverage.calculated_count,
            legacy_recipe_estimated_count=coverage.estimated_count,
            legacy_recipe_blocked_count=coverage.blocked_count,
            items=items,
        )
