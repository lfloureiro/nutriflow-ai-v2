export type NutritionEnrichmentItem = {
  catalog_key: string;
  name: string;
  status: string;
  matched_code: string | null;
  matched_name: string | null;
  confidence: string | null;
  reason: string | null;
  composition_created: boolean;
  recalculated_recipe_count: number;
};

export type NutritionEnrichmentRun = {
  source: string;
  source_version: string;
  cache_refreshed: boolean;
  applied_count: number;
  unit_conversion_count: number;
  review_count: number;
  unmatched_count: number;
  recalculated_recipe_count: number;
  legacy_recipe_total_count: number;
  legacy_recipe_rebuilt_count: number;
  legacy_recipe_calculated_count: number;
  legacy_recipe_estimated_count: number;
  legacy_recipe_blocked_count: number;
  items: NutritionEnrichmentItem[];
};
