import type {
  PracticalSourceKind,
  RecommendationCandidateInput,
  RecommendationHistoryHint,
} from "./types";

export type SharedPracticalRecommendationRequest = {
  person_ids: string[];
  planning_date: string;
  scheduled_at: string;
  meal_type: "breakfast" | "lunch" | "snack" | "dinner";
  candidates: RecommendationCandidateInput[];
  location: string | null;
  available_minutes: number | null;
  has_kitchen: boolean | null;
  source_kinds: PracticalSourceKind[];
  provisional_history: RecommendationHistoryHint[];
  auto_size_portions: boolean;
  max_results: number | null;
};

export type SharedParticipantEvaluation = {
  person_id: string;
  score: string | null;
  quantity: string;
  quantity_unit: string;
  energy_kcal: string | null;
  explanation: string[];
};

export type SharedRecommendationOption = {
  candidate_key: string;
  candidate_name: string;
  candidate_kind: string;
  eligible: boolean;
  rank: number | null;
  minimum_score: string | null;
  average_score: string | null;
  exclusion_reasons: string[];
  participants: [SharedParticipantEvaluation, ...SharedParticipantEvaluation[]];
};

export type SharedPracticalRecommendation = {
  family_id: string;
  person_ids: string[];
  planning_date: string;
  scheduled_at: string;
  meal_type: "breakfast" | "lunch" | "snack" | "dinner";
  engine_version: string;
  source_kinds: string[];
  options: SharedRecommendationOption[];
  commercial_offers: Array<{
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
  }>;
};

export type SharedPracticalPlanRequest = SharedPracticalRecommendationRequest & {
  candidate_key: string;
  title?: string | null;
  notes?: string | null;
};

export type SharedPracticalPlan = {
  meal_event_id: string;
  status: string;
  candidate_key: string;
  person_ids: string[];
  serving_ids: string[];
};
