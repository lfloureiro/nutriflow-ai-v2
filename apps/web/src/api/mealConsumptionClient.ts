import { ApiError, buildApiUrl } from "./client";
import type {
  MealConsumptionResult,
  MealConsumptionUpdate,
} from "./mealPlanTypes";

async function errorMessage(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: unknown };
    if (typeof payload.detail === "string" && payload.detail.length > 0) {
      return payload.detail;
    }
  } catch {
    // Keep the HTTP status fallback for non-JSON responses.
  }
  return response.statusText || `HTTP ${response.status}`;
}

export function mealConsumptionPath(
  familyId: string,
  mealEventId: string,
  personId: string,
  servingId: string,
): string {
  return (
    `/api/families/${encodeURIComponent(familyId)}/meal-plan/` +
    `${encodeURIComponent(mealEventId)}/participants/${encodeURIComponent(personId)}/` +
    `servings/${encodeURIComponent(servingId)}/consumption`
  );
}

export function mealParticipantConsumptionPath(
  familyId: string,
  mealEventId: string,
  personId: string,
): string {
  return (
    `/api/families/${encodeURIComponent(familyId)}/meal-plan/` +
    `${encodeURIComponent(mealEventId)}/participants/${encodeURIComponent(personId)}/consumption`
  );
}

async function patchConsumption(
  path: string,
  payload: MealConsumptionUpdate,
): Promise<MealConsumptionResult> {
  const response = await fetch(buildApiUrl(path), {
    method: "PATCH",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new ApiError(await errorMessage(response), response.status);
  }
  return (await response.json()) as MealConsumptionResult;
}

export async function recordMealConsumption(
  familyId: string,
  mealEventId: string,
  personId: string,
  servingId: string,
  payload: MealConsumptionUpdate,
): Promise<MealConsumptionResult> {
  return patchConsumption(
    mealConsumptionPath(familyId, mealEventId, personId, servingId),
    payload,
  );
}

export async function recordMealParticipantConsumption(
  familyId: string,
  mealEventId: string,
  personId: string,
  payload: MealConsumptionUpdate,
): Promise<MealConsumptionResult> {
  return patchConsumption(
    mealParticipantConsumptionPath(familyId, mealEventId, personId),
    payload,
  );
}
