import { ApiError, buildApiUrl } from "./client";
import type {
  RecipePreferenceSummary,
  RecipeRatingWrite,
} from "./recipePreferenceTypes";

async function errorMessage(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: unknown };
    if (typeof payload.detail === "string" && payload.detail.length > 0) {
      return payload.detail;
    }
  } catch {
    // Non-JSON errors fall through to the HTTP status below.
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

export function recipePreferencesPath(familyId: string, recipeId: string): string {
  return `/api/families/${encodeURIComponent(familyId)}/recipes/${encodeURIComponent(recipeId)}/preferences`;
}

export function getRecipePreferences(
  familyId: string,
  recipeId: string,
): Promise<RecipePreferenceSummary> {
  return request<RecipePreferenceSummary>(recipePreferencesPath(familyId, recipeId));
}

export function setRecipeRating(
  familyId: string,
  recipeId: string,
  personId: string,
  payload: RecipeRatingWrite,
): Promise<RecipePreferenceSummary> {
  return request<RecipePreferenceSummary>(
    `${recipePreferencesPath(familyId, recipeId)}/${encodeURIComponent(personId)}`,
    { method: "PUT", body: JSON.stringify(payload) },
  );
}

export function clearRecipeRating(
  familyId: string,
  recipeId: string,
  personId: string,
): Promise<RecipePreferenceSummary> {
  return request<RecipePreferenceSummary>(
    `${recipePreferencesPath(familyId, recipeId)}/${encodeURIComponent(personId)}`,
    { method: "DELETE" },
  );
}
