import { ApiError, buildApiUrl } from "./client";
import type {
  SharedPracticalPlan,
  SharedPracticalPlanRequest,
  SharedPracticalRecommendation,
  SharedPracticalRecommendationRequest,
} from "./sharedRecommendationTypes";

async function errorMessage(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: unknown };
    if (typeof payload.detail === "string" && payload.detail.length > 0) {
      return payload.detail;
    }
  } catch {
    // Fall through to status text for non-JSON responses.
  }
  return response.statusText || `HTTP ${response.status}`;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  headers.set("Accept", "application/json");
  if (init?.body !== undefined && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const response = await fetch(buildApiUrl(path), { ...init, headers });
  if (!response.ok) {
    throw new ApiError(await errorMessage(response), response.status);
  }
  return (await response.json()) as T;
}

function basePath(familyId: string): string {
  return `/api/families/${encodeURIComponent(familyId)}/meal-recommendations/shared-practical`;
}

export function requestSharedPracticalRecommendation(
  familyId: string,
  payload: SharedPracticalRecommendationRequest,
): Promise<SharedPracticalRecommendation> {
  return request<SharedPracticalRecommendation>(basePath(familyId), {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function planSharedPracticalRecommendation(
  familyId: string,
  payload: SharedPracticalPlanRequest,
): Promise<SharedPracticalPlan> {
  return request<SharedPracticalPlan>(`${basePath(familyId)}/plan`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
