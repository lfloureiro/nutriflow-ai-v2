import { ApiError, buildApiUrl } from "./client";
import type { MealType } from "./mealPlanTypes";

export type MealAttendance = {planning_date: string; meal_type: MealType; person_ids: string[]};
export type WeekSetup = {week_start: string; version: number; attendance?: MealAttendance[]; meal_sources?: Partial<Record<MealType,"home"|"delivery"|"restaurant">>; person_ids: string[]; meal_types: MealType[]; excluded_food_item_ids: string[]};
export type RetailAlternative = {
  id: string; retailer: string; name: string; alternative_group: string; product_url: string;
  pack_quantity: string; pack_unit: string; ingredient_summary: string;
  evidence_level: string; observed_price: string | null; observed_on: string; notes: string;
  nutrition_per_100: Record<string, string> | null; applicable_food_item_ids: string[];
};
async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(buildApiUrl(path), {...init, headers: {Accept: "application/json", "Content-Type": "application/json"}});
  if (!response.ok) {
    const body = await response.json().catch(() => ({})) as {detail?: unknown};
    throw new ApiError(typeof body.detail === "string" ? body.detail : `HTTP ${response.status}`, response.status);
  }
  return response.json() as Promise<T>;
}
const base = (id: string) => `/api/families/${encodeURIComponent(id)}`;
export const getWeekSetup = (familyId: string, week: string) => request<WeekSetup | null>(`${base(familyId)}/planning-setup/${encodeURIComponent(week)}`);
export const saveWeekSetup = (familyId: string, setup: WeekSetup) => request<WeekSetup>(`${base(familyId)}/planning-setup/${encodeURIComponent(setup.week_start)}`, {
  method: "PUT", body: JSON.stringify({person_ids: setup.person_ids, meal_types: setup.meal_types, excluded_food_item_ids: setup.excluded_food_item_ids, attendance: setup.attendance ?? [], meal_sources: setup.meal_sources ?? {}, expected_version: setup.version}),
});
export const listRetailAlternatives = (familyId: string) => request<RetailAlternative[]>(`${base(familyId)}/retail-alternatives`);

export type PlanningRestrictions = {
  excluded_food_item_ids: string[];
  sources: {person_id: string; source_id: string; source_kind: "condition" | "diet"; label: string; food_item_ids: string[]; dates: string[]; meal_types: string[]}[];
  warnings: string[];
};
export const getPlanningRestrictions = (familyId: string, setup: WeekSetup) => request<PlanningRestrictions>(`${base(familyId)}/planning-restrictions`, {
  method: "POST", body: JSON.stringify({person_ids:setup.person_ids,week_start:setup.week_start,meal_types:setup.meal_types,attendance:setup.attendance ?? []}),
});
