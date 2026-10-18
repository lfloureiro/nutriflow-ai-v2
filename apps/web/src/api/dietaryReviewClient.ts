import { ApiError, buildApiUrl } from "./client";

export type HealthCondition = {
  id: string; person_id: string; code: string; name: string;
  status: "reported" | "suspected" | "confirmed" | "resolved";
  source: "user" | "doctor" | "nutritionist" | "document";
  source_reference: string | null; started_on: string | null; ended_on: string | null;
  notes: string | null; version: number; created_at: string; updated_at: string;
};
export type ConditionInput = Omit<HealthCondition, "id" | "person_id" | "version" | "created_at" | "updated_at">;
export type ConditionEvent = { version: number; created_at: string; snapshot: HealthCondition };
export type FodmapReference = {
  id: string; reference_key: string; name_pt: string; name_en: string;
  classification: "high" | "low" | "variable" | "unknown"; fodmap_groups: string[];
  preparation: string; evidence_kind: string; source_name: string; source_url: string;
  source_version: string; retrieved_on: string; notes_pt: string; notes_en: string;
};
export type Substitution = {
  id: string; recipe_ingredient_id: string; replacement_name: string;
  replacement_food_item_id: string | null; replacement_quantity: string | null;
  replacement_unit: string | null; reference_id: string | null;
  status: "proposed" | "reviewed" | "rejected"; notes: string; version: number;
};
export type ReviewIngredient = {
  id: string; food_item_id: string; name: string; quantity: string; unit: string;
  references: FodmapReference[]; substitutions: Substitution[];
};
export type ReviewRecipe = {
  id: string; name: string; source: string; assessment_status: "not_evaluated";
  serving_count?: string | null;
  active_variants?: {id:string;recipe_id:string;name:string;operations:{recipe_ingredient_id:string;replacement_name:string;quantity:string;unit:string;preparation:string}[]}[];
  ingredients: ReviewIngredient[];
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(buildApiUrl(path), {
    ...init, headers: { Accept: "application/json", "Content-Type": "application/json" },
  });
  if (!response.ok) {
    let message = `HTTP ${response.status}`;
    try {
      const body = await response.json() as { detail?: unknown };
      if (typeof body.detail === "string") message = body.detail;
      else if (Array.isArray(body.detail)) message = body.detail.map((v: {msg?: string}) => v.msg ?? "Invalid value").join("; ");
    } catch { /* Use HTTP status if response is not JSON. */ }
    throw new ApiError(message, response.status);
  }
  return response.json() as Promise<T>;
}
const familyPath = (id: string) => `/api/families/${encodeURIComponent(id)}`;
const conditionsPath = (familyId: string, personId: string) =>
  `${familyPath(familyId)}/persons/${encodeURIComponent(personId)}/conditions`;

export const listConditions = (familyId: string, personId: string) =>
  request<HealthCondition[]>(conditionsPath(familyId, personId));
export const saveCondition = (familyId: string, personId: string, input: ConditionInput, current?: HealthCondition) =>
  request<HealthCondition>(conditionsPath(familyId, personId) + (current ? `/${encodeURIComponent(current.id)}` : ""), {
    method: current ? "PUT" : "POST",
    body: JSON.stringify(current ? {...input, expected_version: current.version} : input),
  });
export const conditionHistory = (familyId: string, personId: string, id: string) =>
  request<ConditionEvent[]>(`${conditionsPath(familyId, personId)}/${encodeURIComponent(id)}/history`);
export const listRecipeReviews = (familyId: string) =>
  request<ReviewRecipe[]>(`${familyPath(familyId)}/recipe-adaptations`);
export const listFodmapReferences = (familyId: string) =>
  request<FodmapReference[]>(`${familyPath(familyId)}/fodmap-references`);
export const createSubstitution = (familyId: string, input: {
  recipe_ingredient_id: string; replacement_name: string; notes: string;
  reference_id?: string | null; replacement_quantity?: string | null; replacement_unit?: string | null;
}) => request<Substitution>(`${familyPath(familyId)}/recipe-adaptations`, {
  method: "POST", body: JSON.stringify(input),
});
export const reviewSubstitution = (familyId: string, row: Substitution, status: Substitution["status"], notes: string, quantity?: {replacement_quantity:string|null;replacement_unit:string|null}) =>
  request<Substitution>(`${familyPath(familyId)}/recipe-adaptations/${encodeURIComponent(row.id)}`, {
    method: "PUT", body: JSON.stringify({ expected_version: row.version, status, notes, ...quantity }),
  });
