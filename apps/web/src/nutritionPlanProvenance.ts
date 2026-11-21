import type { NutritionPlanSummary } from "./api/planFitTypes";

/** Pure metadata presentation: a declared professional source is not proof of verification. */
export function nutritionPlanProvenance(plan: NutritionPlanSummary) {
  return {
    declaredSource: plan.source_name?.trim() || null,
    sourceType: plan.source_type.replaceAll("_"," "),
    reference: plan.source_reference?.trim() || null,
    version: plan.version,
    openEnded: plan.valid_until === null,
    professionalVerification: "not_verified_in_app" as const,
  };
}
