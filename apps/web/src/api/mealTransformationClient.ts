import { ApiError, buildApiUrl } from "./client";
import type {
  MealTransformationRequest,
  MealTransformationResult,
} from "./mealTransformationTypes";

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

export async function proposeMealTransformations(
  personId: string,
  payload: MealTransformationRequest,
): Promise<MealTransformationResult> {
  const response = await fetch(
    buildApiUrl(
      `/api/persons/${encodeURIComponent(personId)}/meal-transformations/proposals`,
    ),
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
  return (await response.json()) as MealTransformationResult;
}
