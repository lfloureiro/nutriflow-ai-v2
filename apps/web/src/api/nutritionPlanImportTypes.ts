export type NutritionPlanImportConfirmationStatus = "proposed" | "confirmed" | "rejected";
export type NutritionPlanImportProposalType =
  | "numeric_rule"
  | "qualitative_guideline"
  | "frequency_guideline"
  | "unclassified";

export interface NutritionPlanImportProposal {
  id: string;
  import_session_id: string;
  ordinal: number;
  source_statement: string;
  proposal_type: NutritionPlanImportProposalType;
  target_type: string | null;
  target_key: string | null;
  operator: string | null;
  value_min: string | null;
  value_max: string | null;
  value_target: string | null;
  unit: string | null;
  description: string | null;
  meal_type: "breakfast" | "lunch" | "snack" | "dinner" | null;
  period: string | null;
  minimum_occurrences: number | null;
  maximum_occurrences: number | null;
  severity: string;
  is_mandatory: boolean;
  priority: number;
  valid_from: string | null;
  valid_until: string | null;
  confidence: string;
  confirmation_status: NutritionPlanImportConfirmationStatus;
  parser_note: string | null;
  review_notes: string | null;
  nutrition_plan_rule_id: string | null;
  nutrition_plan_guideline_id: string | null;
}

export interface ImportedNutritionPlan {
  id: string;
  title: string;
  source_type: string;
  source_name: string | null;
  source_reference: string | null;
  status: "draft" | "active" | "inactive" | "superseded";
  valid_from: string;
  valid_until: string | null;
}

export interface NutritionPlanImportSession {
  id: string;
  person_id: string;
  nutrition_plan_id: string;
  parser_name: string;
  parser_version: string;
  status: "review" | "applied" | "cancelled";
  source_text: string;
  parse_summary: string | null;
  nutrition_plan: ImportedNutritionPlan;
  proposals: NutritionPlanImportProposal[];
}

export interface NutritionPlanImportCreate {
  title: string;
  source_type: "nutritionist" | "clinician" | "user" | "system" | "imported";
  source_name: string | null;
  source_reference: string | null;
  source_text: string;
  valid_from: string;
  valid_until: string | null;
}

export interface NutritionPlanChatGPTPrompt {
  prompt: string;
}

export interface NutritionPlanChatGPTImportCreate {
  plan: NutritionPlanImportCreate;
  response_text: string;
}

export interface NutritionPlanDocumentExtraction {
  filename: string;
  content_type: string | null;
  document_type: "pdf" | "docx" | "text";
  source_text: string;
  character_count: number;
  extractor_name: string;
  extractor_version: string;
  warnings: string[];
}
