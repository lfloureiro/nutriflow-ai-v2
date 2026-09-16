import type { MealPlanFitResult } from "./planFitTypes";
import type { PlanningMealType } from "./types";

export type MealTransformationRequest = {
  planning_date: string;
  meal_type: PlanningMealType;
  recipe_id: string;
  quantity: string;
  quantity_unit: string;
  daily_nutrition_state_id?: string | null;
  max_proposals?: number;
};

export type MealTransformationOperation = {
  operation_type: "replace_ingredient";
  substitution_group: string;
  recipe_ingredient_id: string;
  source_food_item_id: string;
  source_food_name: string;
  source_quantity: string;
  source_unit: string;
  replacement_food_item_id: string;
  replacement_food_name: string;
  replacement_quantity: string;
  replacement_unit: string;
};

export type MealTransformationProposal = {
  operation: MealTransformationOperation;
  before_fit: MealPlanFitResult;
  after_fit: MealPlanFitResult;
  fit_score_delta: string | null;
  resolves_mandatory_block: boolean;
  changed_rule_ids: string[];
  explanation: string[];
};

export type MealTransformationResult = {
  person_id: string;
  recipe_id: string;
  recipe_name: string;
  planning_date: string;
  meal_type: PlanningMealType;
  baseline_fit: MealPlanFitResult;
  proposals: MealTransformationProposal[];
  limitations: string[];
};
