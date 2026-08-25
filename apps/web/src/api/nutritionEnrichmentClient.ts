import { ApiError, buildApiUrl } from "./client";
import type { NutritionEnrichmentRun } from "./nutritionEnrichmentTypes";

async function responseError(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: unknown };
    if (typeof payload.detail === "string" && payload.detail.length > 0) {
      return payload.detail;
    }
  } catch {
    // Fall through to the HTTP status text.
  }
  return response.statusText || `HTTP ${response.status}`;
}

export async function autoEnrichNutrition(
  familyId: string,
  options: { refresh?: boolean; limit?: number } = {},
): Promise<NutritionEnrichmentRun> {
  const query = new URLSearchParams({
    refresh: options.refresh ? "true" : "false",
    limit: String(options.limit ?? 200),
  });
  const response = await fetch(
    buildApiUrl(
      `/api/families/${encodeURIComponent(familyId)}/nutrition-enrichment/auto?${query.toString()}`,
    ),
    {
      method: "POST",
      headers: { Accept: "application/json" },
    },
  );
  if (!response.ok) {
    throw new ApiError(await responseError(response), response.status);
  }
  return (await response.json()) as NutritionEnrichmentRun;
}
