import { ApiError, buildApiUrl } from "./client";
import type { MealPlanFitRequest, MealPlanFitResult } from "./planFitTypes";

async function errorMessage(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: unknown };
    if (typeof payload.detail === "string" && payload.detail.length > 0) {
      return payload.detail;
    }
  } catch {
    // Fall through to HTTP status text.
  }
  return response.statusText || `HTTP ${response.status}`;
}

export async function evaluateMealPlanFit(
  personId: string,
  payload: MealPlanFitRequest,
): Promise<MealPlanFitResult> {
  const response = await fetch(
    buildApiUrl(`/api/persons/${encodeURIComponent(personId)}/meal-plan-fit`),
    {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    },
  );
  if (!response.ok) {
    throw new ApiError(await errorMessage(response), response.status);
  }
  return (await response.json()) as MealPlanFitResult;
}
