import { describe, expect, it } from "vitest";

import type { MealPlanFitRule } from "./api/planFitTypes";
import {
  formatPlanFitNumber,
  planFitRuleExplanation,
  planFitTargetLabel,
  planFitUnitLabel,
} from "./mealPlanFitPresentation";

function rule(overrides: Partial<MealPlanFitRule> = {}): MealPlanFitRule {
  return {
    rule_id: "rule-1",
    target_type: "nutrient",
    target_key: "protein",
    operator: "min",
    scope: "meal",
    status: "pass",
    is_mandatory: true,
    priority: 1,
    observed_value: "18.0000",
    observed_unit: "g",
    projected_daily_value: null,
    target_min: "15.0000",
    target_max: null,
    target_value: null,
    target_unit: "g",
    score: "1.0000",
    explanation: "Candidate meets the minimum.",
    source: {
      plan_id: null,
      plan_title: null,
      plan_source_type: null,
      source_name: "demo",
      source_reference: null,
      rule_source: null,
    },
    ...overrides,
  };
}

describe("Plan-Fit presentation localization", () => {
  it("uses PT-PT nutrient labels and units", () => {
    expect(planFitTargetLabel("protein", "pt-PT")).toBe("Proteína");
    expect(planFitTargetLabel("sodium", "pt-PT")).toBe("Sódio");
    expect(planFitUnitLabel("serving", "pt-PT", 1)).toBe("porção");
    expect(planFitUnitLabel("serving", "pt-PT", 2)).toBe("porções");
  });

  it("removes storage precision from displayed numbers", () => {
    expect(formatPlanFitNumber("15.0000", "pt-PT")).toBe("15");
    expect(formatPlanFitNumber("14.5000", "pt-PT")).toBe("14,5");
  });

  it("does not expose backend English explanations in PT-PT", () => {
    expect(planFitRuleExplanation(rule(), "pt-PT")).toBe("A porção cumpre o mínimo.");
    expect(
      planFitRuleExplanation(
        rule({ scope: "daily", status: "support", projected_daily_value: "19.0000" }),
        "pt-PT",
      ),
    ).toBe("Esta porção aproxima o total diário do mínimo, mas ainda não o atinge.");
  });
});
