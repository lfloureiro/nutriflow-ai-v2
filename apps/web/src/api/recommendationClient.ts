import { ApiError, buildApiUrl } from "./client";
import type { PlanningBootstrap } from "./types";

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

export async function getRecommendationBootstrap(
  personId: string,
  scheduledAt: string,
): Promise<PlanningBootstrap> {
  const query = new URLSearchParams({ scheduled_at: scheduledAt, ensure_state: "true" });
  const path = `/api/persons/${encodeURIComponent(personId)}/planning-bootstrap?${query.toString()}`;
  const response = await fetch(buildApiUrl(path), {
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    throw new ApiError(await responseError(response), response.status);
  }
  return (await response.json()) as PlanningBootstrap;
}
