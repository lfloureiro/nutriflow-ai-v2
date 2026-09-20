import type { MealTransformationOperation } from "./mealTransformationTypes";
import type {
  MealPlanFitGuideline,
  MealPlanFitNutrient,
  MealPlanFitRule,
  PlanFitConflict,
} from "./planFitTypes";
import type { RecommendationCandidateInput } from "./types";

export type WeeklyPlanningMealType = "breakfast" | "lunch" | "snack" | "dinner";
export type NutritionPlanAuthorityState =
  | "active_plan"
  | "partial_plan_coverage"
  | "no_active_plan"
  | "plan_conflict";
export type MealPlanFitStatus = "pass" | "partial" | "fail" | "unknown" | "conflict";

export type SharedWeeklyPlanningSlotRequest = {
  slot_key: string;
  planning_date: string;
  scheduled_at: string;
  meal_type: WeeklyPlanningMealType;
  candidates: RecommendationCandidateInput[];
  location: string | null;
  available_minutes: number | null;
  has_kitchen: boolean | null;
  source_kinds: string[];
  delivery_provider_keys: string[];
  provisional_history: { plan_date: string; candidate_key: string }[];
  auto_size_portions: boolean;
};

export type SharedWeeklyPlanPinnedChoice = {
  slot_key: string;
  candidate_key: string;
  recipe_ingredient_id?: string | null;
  replacement_food_item_id?: string | null;
};

export type SharedWeeklyPlanProposalRequest = {
  person_ids: string[];
  slots: SharedWeeklyPlanningSlotRequest[];
  pinned_choices?: SharedWeeklyPlanPinnedChoice[];
  max_combinations?: number;
};

export type SharedWeeklyPlanTransformation = {
  kind: "plan_adapted" | "preference_variant";
  recipe_id: string;
  operation: MealTransformationOperation;
  plan_improvement_participants: number;
  preference_improvement_participants: number;
  explanation: string[];
};

export type SharedWeeklyPlanExpectedChoice = {
  slot_key: string;
  candidate_key: string;
  recipe_ingredient_id?: string | null;
  replacement_food_item_id?: string | null;
};

export type SharedWeeklyPlanRequest = SharedWeeklyPlanProposalRequest & {
  expected_choices: SharedWeeklyPlanExpectedChoice[];
};

export type SharedWeeklyPlanMaterializedChoice = {
  slot_key: string;
  meal_event_id: string;
  candidate_key: string;
  transformation_application_id: string | null;
  serving_ids: string[];
};

export type SharedWeeklyPlan = {
  family_id: string;
  status: "planned";
  choices: SharedWeeklyPlanMaterializedChoice[];
};

export type SharedWeeklyPlanParticipant = {
  person_id: string;
  daily_nutrition_state_id: string | null;
  score: string | null;
  quantity: string;
  quantity_unit: string;
  energy_kcal: string | null;
  nutrition: {
    energy_kcal: string | null;
    nutrients: Record<string, MealPlanFitNutrient>;
  };
  plan_fit_detail: {
    eligible: boolean;
    status: MealPlanFitStatus;
    fit_score: string | null;
    conflicts: PlanFitConflict[];
    safety_issues: string[];
    rule_results: MealPlanFitRule[];
    guideline_results: MealPlanFitGuideline[];
  };
  portion_factor: string | null;
  meal_energy_target_min_kcal: string | null;
  meal_energy_target_max_kcal: string | null;
  nutrition_plan_authority: NutritionPlanAuthorityState;
  active_plan_titles: string[];
  explanation: string[];
};

export type SharedWeeklyPlanChoice = {
  slot_key: string;
  planning_date: string;
  scheduled_at: string;
  meal_type: WeeklyPlanningMealType;
  candidate_key: string;
  candidate_name: string;
  candidate_kind: string;
  recipe_id: string | null;
  minimum_score: string | null;
  average_score: string | null;
  participants: SharedWeeklyPlanParticipant[];
  transformation: SharedWeeklyPlanTransformation | null;
};

export type SharedWeeklyPlanSelection = {
  mandatory_support_participants: number;
  mandatory_support_total: number;
  advisory_support_participants: number;
  advisory_support_total: number;
  minimum_participant_score: string;
  average_participant_score: string;
  repeated_candidate_count: number;
  choices: SharedWeeklyPlanChoice[];
};

export type SharedWeeklyPlanSkippedSlot = {
  slot_key: string;
  planning_date: string;
  meal_type: WeeklyPlanningMealType;
  reason: "no_eligible_candidates";
  exclusion_reasons: string[];
};

export type SharedWeeklyPlanProposal = {
  family_id: string;
  participant_ids: string[];
  week_start: string;
  week_end: string;
  engine_version: string;
  slot_engine_versions: Record<string, string>;
  selected_plan: SharedWeeklyPlanSelection | null;
  skipped_slots: SharedWeeklyPlanSkippedSlot[];
  evaluated_combinations: number;
  feasible_combinations: number;
  rejected_by_person_weekly_maximum: number;
  rejected_by_person_daily_limit: number;
  search_strategy: "exact" | "bounded" | string;
  search_space_size: number;
  search_truncated: boolean;
};
