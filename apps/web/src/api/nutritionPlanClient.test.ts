import { describe, expect, it } from "vitest";

import {
  summarizeNutritionPlanAuthority,
  type NutritionPlanAuthorityOverview,
} from "./nutritionPlanClient";
import type {
  EffectiveNutritionPlan,
  NutritionPlanAuthorityState,
  NutritionPlanSummary,
} from "./planFitTypes";
import type { PlanningMealType } from "./types";

const mealTypes: PlanningMealType[] = ["breakfast", "lunch", "snack", "dinner"];

function plan(id = "plan-1"): NutritionPlanSummary {
  return {
    id,
    person_id: "person-1",
    lineage_id: "lineage-1",
    version: 1,
    supersedes_plan_id: null,
    title: "Plano do nutricionista",
    source_type: "nutritionist",
    source_name: "Dra. Demo",
    source_reference: null,
    original_text: null,
    status: "active",
    valid_from: "2026-09-01",
    valid_until: null,
    created_at: "2026-09-01T00:00:00Z",
    updated_at: "2026-09-01T00:00:00Z",
  };
}

function effective(
  mealType: PlanningMealType,
  state: NutritionPlanAuthorityState,
  activePlans: NutritionPlanSummary[] = state === "no_active_plan" ? [] : [plan()],
): EffectiveNutritionPlan {
  return {
    person_id: "person-1",
    effective_date: "2026-09-17",
    meal_type: mealType,
    active_plans: activePlans,
    nutrition_plan_authority: {
      state,
      active_plans: activePlans,
      plan_rule_ids: [],
      plan_guideline_ids: [],
      unknown_evidence: [],
      explanation: [],
    },
  };
}

function summarize(states: NutritionPlanAuthorityState[]): NutritionPlanAuthorityOverview {
  return summarizeNutritionPlanAuthority(
    states.map((state, index) => effective(mealTypes[index], state)),
  );
}

describe("summarizeNutritionPlanAuthority", () => {
  it("reports no active plan only when every meal has no active plan", () => {
    expect(
      summarize([
        "no_active_plan",
        "no_active_plan",
        "no_active_plan",
        "no_active_plan",
      ]).state,
    ).toBe("no_active_plan");
  });

  it("reports active plan only when every meal has applicable plan guidance", () => {
    expect(
      summarize(["active_plan", "active_plan", "active_plan", "active_plan"]).state,
    ).toBe("active_plan");
  });

  it("reports partial coverage for mixed meal coverage", () => {
    expect(
      summarize([
        "active_plan",
        "partial_plan_coverage",
        "active_plan",
        "partial_plan_coverage",
      ]).state,
    ).toBe("partial_plan_coverage");
  });

  it("lets any mandatory plan conflict dominate the overview", () => {
    expect(
      summarize([
        "active_plan",
        "plan_conflict",
        "partial_plan_coverage",
        "active_plan",
      ]).state,
    ).toBe("plan_conflict");
  });

  it("deduplicates active plan provenance across meals", () => {
    const shared = plan();
    const overview = summarizeNutritionPlanAuthority(
      mealTypes.map((mealType) => effective(mealType, "active_plan", [shared])),
    );

    expect(overview.active_plans).toHaveLength(1);
    expect(overview.active_plans[0].id).toBe(shared.id);
  });
});
