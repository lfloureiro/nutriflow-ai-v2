import { ApiError, buildApiUrl } from "./client";
import type {
  SharedMealTransformationPlan,
  SharedMealTransformationPlanRequest,
  SharedMealTransformationRequest,
  SharedMealTransformationResult,
} from "./sharedMealTransformationTypes";

async function responseError(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: unknown };
    if (typeof payload.detail === "string" && payload.detail.length > 0) {
      return payload.detail;
    }
  } catch {
    // Fall through to status text.
  }
  return response.statusText || `HTTP ${response.status}`;
}

export function sharedMealTransformationPath(familyId: string): string {
  return `/api/families/${encodeURIComponent(familyId)}/meal-transformations/proposals`;
}

export function sharedMealTransformationPlanPath(familyId: string): string {
  return `/api/families/${encodeURIComponent(familyId)}/meal-transformations/plan`;
}

export async function proposeSharedMealTransformations(
  familyId: string,
  payload: SharedMealTransformationRequest,
): Promise<SharedMealTransformationResult> {
  const response = await fetch(
    buildApiUrl(sharedMealTransformationPath(familyId)),
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
    throw new ApiError(await responseError(response), response.status);
  }
  return (await response.json()) as SharedMealTransformationResult;
}


export async function planSharedMealTransformation(
  familyId: string,
  payload: SharedMealTransformationPlanRequest,
): Promise<SharedMealTransformationPlan> {
  const response = await fetch(
    buildApiUrl(sharedMealTransformationPlanPath(familyId)),
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
    throw new ApiError(await responseError(response), response.status);
  }
  return (await response.json()) as SharedMealTransformationPlan;
}
