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
