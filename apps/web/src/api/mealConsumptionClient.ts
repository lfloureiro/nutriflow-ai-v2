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

export async function recordMealConsumption(
  familyId: string,
  mealEventId: string,
  personId: string,
  servingId: string,
  payload: MealConsumptionUpdate,
): Promise<MealConsumptionResult> {
  const path =
    `/api/families/${encodeURIComponent(familyId)}/meal-plan/` +
    `${encodeURIComponent(mealEventId)}/participants/${encodeURIComponent(personId)}/` +
    `servings/${encodeURIComponent(servingId)}/consumption`;
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
