export type Person = {
  id: string;
  family_id: string;
  first_name: string;
  last_name: string | null;
  birth_date: string | null;
  preferred_locale: string;
  timezone: string;
  created_at: string;
  updated_at: string;
};

export type FamilyDashboardHealth = {
  state_date: string;
  latest_weight_kg: string | null;
  weight_trend_7d_kg: string | null;
  weight_trend_28d_kg: string | null;
  steps: number | null;
  active_energy_kcal: string | null;
  sleep_duration_minutes: number | null;
  resting_heart_rate_bpm: string | null;
  hrv_ms: string | null;
  training_load: string | null;
  confidence_score: string | null;
  computed_at: string;
};

export type FamilyDashboardNutrition = {
  state_date: string;
  energy_consumed_kcal: string;
  energy_planned_kcal: string;
  energy_remaining_min_kcal: string | null;
  energy_remaining_max_kcal: string | null;
  adherence_score: string | null;
  confidence_score: string | null;
  computed_at: string;
};

export type FamilyDashboardMember = {
  person_id: string;
  first_name: string;
  last_name: string | null;
  timezone: string;
  health: FamilyDashboardHealth | null;
  nutrition: FamilyDashboardNutrition | null;
};

export type FamilyDashboardMeal = {
  id: string;
  meal_type: string;
  title: string | null;
  scheduled_at: string;
  timezone: string;
  status: string;
  location: string | null;
  participant_person_ids: string[];
};

export type FamilyDashboard = {
  family_id: string;
  family_name: string;
  timezone: string;
  dashboard_date: string;
  members: FamilyDashboardMember[];
  meals: FamilyDashboardMeal[];
};

export type FamilyMealParticipant = {
  person_id: string;
  first_name: string;
  last_name: string | null;
  status: string;
};

export type FamilyMeal = {
  id: string;
  meal_type: string;
  title: string | null;
  scheduled_at: string;
  timezone: string;
  status: string;
  location: string | null;
  participants: FamilyMealParticipant[];
};

export type FamilyMealsDay = {
  date: string;
  meals: FamilyMeal[];
};

export type FamilyMeals = {
  family_id: string;
  family_name: string;
  timezone: string;
  start_date: string;
  end_date: string;
  days: FamilyMealsDay[];
};

export type PracticalSourceKind =
  | "home"
  | "pantry"
  | "restaurant"
  | "delivery"
  | "store";

export type RecommendationCandidateInput = {
  candidate_kind: "food_item" | "recipe";
  composition_id: string;
  quantity: string;
  quantity_unit: string;
};

export type RecommendationHistoryHint = {
  plan_date: string;
  candidate_key: string;
};

export type PlanningNutritionComponent = {
  target_type: string;
  target_key: string;
  consumed_value: string | null;
  planned_value: string | null;
  remaining_min: string | null;
  remaining_max: string | null;
  unit: string;
};

export type PlanningDailyNutritionState = {
  id: string;
  state_date: string;
  timezone: string;
  energy_consumed_kcal: string;
  energy_planned_kcal: string;
  energy_assumed_kcal: string;
  energy_remaining_min_kcal: string | null;
  energy_remaining_max_kcal: string | null;
  calculation_version: string;
  computed_at: string;
  components: PlanningNutritionComponent[];
};

export type PlanningCandidate = {
  candidate_kind: "food_item" | "recipe";
  composition_id: string;
  catalog_key: string;
  name: string;
  category: string;
  brand: string | null;
  description: string | null;
  reference_quantity: string;
  reference_unit: string;
  energy_kcal: string | null;
  composition_version: string;
  composition_at: string;
};

export type PlanningBootstrap = {
  person_id: string;
  family_id: string;
  scheduled_at: string;
  planning_date: string;
  daily_nutrition_state: PlanningDailyNutritionState | null;
  candidates: PlanningCandidate[];
};

export type PracticalRecommendationRequest = {
  daily_nutrition_state_id: string;
  planning_date: string;
  scheduled_at: string;
  meal_type: string | null;
  candidates: RecommendationCandidateInput[];
  location: string | null;
  available_minutes: number | null;
  has_kitchen: boolean | null;
  source_kinds: PracticalSourceKind[];
  provisional_history: RecommendationHistoryHint[];
  auto_size_portions: boolean;
  max_results: number | null;
};

export type RecommendationNutrient = {
  value: string;
  unit: string;
};

export type RecommendationOption = {
  id: string;
  candidate_key: string;
  candidate_name: string;
  candidate_kind: string;
  quantity: string;
  quantity_unit: string;
  eligible: boolean;
  rank: number | null;
  score: string | null;
  score_breakdown: Record<string, string>;
  exclusion_reasons: string[];
  explanation: string[];
  nutrition: {
    energy_kcal: string | null;
    nutrients: Record<string, RecommendationNutrient>;
  };
};

export type CommercialOffer = {
  candidate_key: string;
  source_kind: string;
  source_key: string;
  location: string | null;
  offer_key: string;
  provider_key: string;
  provider_name: string | null;
  item_price: string;
  currency: string;
  delivery_fee: string | null;
  minimum_order: string | null;
  total_known_price: string;
  observed_at: string;
  source_reference: string | null;
};

export type PracticalRecommendationRun = {
  id: string;
  person_id: string;
  daily_nutrition_state_id: string;
  planning_date: string;
  meal_type: string | null;
  engine_version: string;
  scheduled_at: string;
  location: string | null;
  source_kinds: string[];
  options: RecommendationOption[];
  commercial_offers: CommercialOffer[];
};

export type RecommendationDecisionRequest = {
  action: "accepted" | "rejected" | "modified";
  scheduled_at?: string | null;
  timezone?: string | null;
  quantity?: string | null;
  quantity_unit?: string | null;
  meal_type?: string | null;
  title?: string | null;
  location?: string | null;
  notes?: string | null;
  feedback_metadata?: Record<string, unknown> | null;
};

export type RecommendationDecision = {
  feedback_id: string;
  recommendation_option_id: string;
  action: "accepted" | "rejected" | "modified";
  resulting_serving_id: string | null;
  meal_event_id: string | null;
  meal_event_status: string | null;
  scheduled_at: string | null;
  quantity_planned: string | null;
  quantity_unit: string | null;
  energy_planned_kcal: string | null;
};
