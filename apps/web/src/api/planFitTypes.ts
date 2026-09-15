import type { PlanningMealType, RecommendationCandidateInput } from "./types";

export type NutritionPlanSummary = {
  id: string;
  person_id: string;
  lineage_id: string;
  version: number;
  supersedes_plan_id: string | null;
  title: string;
  source_type: string;
  source_name: string | null;
  source_reference: string | null;
  original_text: string | null;
  status: string;
  valid_from: string;
  valid_until: string | null;
  created_at: string;
  updated_at: string;
};

export type PlanFitSource = {
  plan_id: string | null;
  plan_title: string | null;
  plan_source_type: string | null;
  source_name: string | null;
  source_reference: string | null;
  rule_source: string | null;
};

export type PlanFitConflict = {
  target_type: string;
  target_key: string;
  unit: string | null;
  severity: "mandatory" | "advisory";
  rule_ids: string[];
  message: string;
};

export type MealPlanFitRequest = {
  planning_date: string;
  meal_type: PlanningMealType;
  candidate: RecommendationCandidateInput;
  daily_nutrition_state_id?: string | null;
};

export type MealPlanFitNutrient = {
  value: string;
  unit: string;
};

export type MealPlanFitCandidate = {
  key: string;
  name: string;
  kind: string;
  quantity: string;
  quantity_unit: string;
  nutrition: {
    energy_kcal: string | null;
    nutrients: Record<string, MealPlanFitNutrient>;
  };
};

export type MealPlanFitRule = {
  rule_id: string;
  target_type: string;
  target_key: string;
  operator: string;
  scope: "candidate" | "meal" | "daily";
  status: "pass" | "fail" | "support" | "unknown" | "not_evaluated";
  is_mandatory: boolean;
  priority: number;
  observed_value: string | null;
  observed_unit: string | null;
  projected_daily_value: string | null;
  target_min: string | null;
  target_max: string | null;
  target_value: string | null;
  target_unit: string | null;
  score: string | null;
  explanation: string;
  source: PlanFitSource;
};

export type MealPlanFitGuideline = {
  guideline_id: string;
  description: string;
  is_mandatory: boolean;
  priority: number;
  status: "not_evaluated";
  explanation: string;
  source: PlanFitSource;
};

export type MealPlanFitResult = {
  person_id: string;
  planning_date: string;
  meal_type: PlanningMealType;
  daily_nutrition_state_id: string | null;
  candidate: MealPlanFitCandidate;
  eligible: boolean;
  status: "pass" | "partial" | "fail" | "unknown" | "conflict";
  fit_score: string | null;
  active_plans: NutritionPlanSummary[];
  conflicts: PlanFitConflict[];
  safety_issues: string[];
  rule_results: MealPlanFitRule[];
  guideline_results: MealPlanFitGuideline[];
  explanation: string[];
};
