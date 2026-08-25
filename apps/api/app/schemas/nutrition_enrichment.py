from decimal import Decimal

from pydantic import BaseModel


class NutritionEnrichmentItemRead(BaseModel):
    catalog_key: str
    name: str
    status: str
    matched_code: str | None
    matched_name: str | None
    confidence: Decimal | None
    reason: str | None
    composition_created: bool
    recalculated_recipe_count: int


class NutritionEnrichmentRunRead(BaseModel):
    source: str
    source_version: str
    cache_refreshed: bool
    applied_count: int
    unit_conversion_count: int
    review_count: int
    unmatched_count: int
    recalculated_recipe_count: int
    legacy_recipe_total_count: int
    legacy_recipe_rebuilt_count: int
    legacy_recipe_calculated_count: int
    legacy_recipe_estimated_count: int
    legacy_recipe_blocked_count: int
    items: list[NutritionEnrichmentItemRead]
