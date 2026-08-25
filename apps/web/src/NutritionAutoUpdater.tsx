import { useEffect } from "react";

import { autoEnrichNutrition } from "./api/nutritionEnrichmentClient";

export const NUTRITION_ENRICHED_EVENT = "nutriflow:nutrition-enriched";

export default function NutritionAutoUpdater({ familyId }: { familyId: string }) {
  useEffect(() => {
    let cancelled = false;
    void autoEnrichNutrition(familyId)
      .then((result) => {
        const changeCount = result.applied_count + result.unit_conversion_count;
        if (cancelled || changeCount === 0) return;
        window.dispatchEvent(
          new CustomEvent(NUTRITION_ENRICHED_EVENT, {
            detail: {
              appliedCount: result.applied_count,
              unitConversionCount: result.unit_conversion_count,
              recalculatedRecipeCount: result.recalculated_recipe_count,
              source: result.source,
              sourceVersion: result.source_version,
            },
          }),
        );
      })
      .catch(() => {
        // Enrichment is best-effort and must never block normal navigation.
      });
    return () => {
      cancelled = true;
    };
  }, [familyId]);

  return null;
}
