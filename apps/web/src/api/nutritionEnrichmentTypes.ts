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
  review_count: number;
  unmatched_count: number;
  recalculated_recipe_count: number;
  items: NutritionEnrichmentItem[];
};
