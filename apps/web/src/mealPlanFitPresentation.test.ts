import { describe, expect, it } from "vitest";

import type { MealPlanFitResult, MealPlanFitRule } from "./api/planFitTypes";
import {
  formatPlanFitNumber,
  planFitEvidenceSource,
  planFitEvidenceSummary,
  planFitCandidateNutrition,
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
  it("keeps unknown evidence distinct from passing and mandatory failures", () => {
    const passing=rule({rule_id:"passed"});
    const unknown=rule({rule_id:"unknown",status:"unknown"});
    const mandatory=rule({rule_id:"mandatory",status:"fail",is_mandatory:true});
    const result={
      rule_results:[passing,unknown,mandatory],
      guideline_results:[{status:"not_evaluated"},{status:"not_evaluated"}],
    } as unknown as MealPlanFitResult;
    expect(planFitEvidenceSummary(result)).toEqual({
      evaluated:2, unknown:1, unevaluatedGuidelines:2, blocking:1,
    });
  });

  it("shows only explicitly supplied provenance and never fabricates a source", () => {
    expect(planFitEvidenceSource(rule().source,"pt-PT")).toEqual(["Demo"]);
    expect(planFitEvidenceSource({
      ...rule().source,plan_title:"Plano exemplo",
      source_name:"Clínica QA",source_reference:"Relatório 2026",
    },"pt-PT")).toEqual(["Plano exemplo","Clínica QA","Relatório 2026"]);
    expect(planFitEvidenceSource({
      ...rule().source, source_name:null,
    },"pt-PT")).toEqual([]);
  });

  it("uses candidate portion values without inventing missing energy or nutrient zeros", () => {
    const result={
      candidate:{nutrition:{energy_kcal:null,nutrients:{
        protein:{value:"18.4",unit:"g"},
        fiber:{value:"2.0",unit:"g"},
        unknown:{value:"not-a-number",unit:"g"},
        blank:{value:"",unit:"g"},
      }}},
    } as unknown as MealPlanFitResult;
    expect(planFitCandidateNutrition(result)).toEqual({
      energyKcal:null,
      nutrients:[{key:"fiber",value:"2.0",unit:"g"},{key:"protein",value:"18.4",unit:"g"}],
    });
    expect(planFitCandidateNutrition({
      candidate:{nutrition:{energy_kcal:"350",nutrients:{}}},
    } as unknown as MealPlanFitResult)).toEqual({energyKcal:"350",nutrients:[]});
  });

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
