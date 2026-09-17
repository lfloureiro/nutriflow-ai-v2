import type { MealPlanFitResult } from "./planFitTypes";
import type { MealTransformationOperation } from "./mealTransformationTypes";
import type { PlanningMealType } from "./types";

export type SharedMealTransformationKind =
  | "plan_adapted"
  | "preference_variant";

export type SharedMealTransformationParticipantRequest = {
  person_id: string;
  daily_nutrition_state_id?: string | null;
  quantity: string;
  quantity_unit: string;
};

export type SharedMealTransformationRequest = {
  planning_date: string;
  meal_type: PlanningMealType;
  recipe_id: string;
  participants: SharedMealTransformationParticipantRequest[];
  max_proposals?: number;
};

export type SharedMealTransformationParticipantResult = {
  person_id: string;
  before_fit: MealPlanFitResult;
  after_fit: MealPlanFitResult;
  plan_score_delta: string | null;
  plan_improved_rule_ids: string[];
  plan_worsened_rule_ids: string[];
  preference_delta: string;
};

export type SharedMealTransformationProposal = {
  kind: SharedMealTransformationKind;
  operation: MealTransformationOperation;
  participant_results: SharedMealTransformationParticipantResult[];
  plan_improvement_participants: number;
  preference_improvement_participants: number;
  minimum_plan_score_delta: string | null;
  average_plan_score_delta: string | null;
  minimum_preference_delta: string;
  average_preference_delta: string;
  explanation: string[];
};

export type SharedMealTransformationResult = {
  family_id: string;
  recipe_id: string;
  recipe_name: string;
  planning_date: string;
  meal_type: PlanningMealType;
  baseline: Array<{
    person_id: string;
    fit: MealPlanFitResult;
  }>;
  proposals: SharedMealTransformationProposal[];
  limitations: string[];
};
