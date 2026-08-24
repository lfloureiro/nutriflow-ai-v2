import { ApiError, buildApiUrl } from "./client";
import type {
  MealDeliveryProviderKey,
  MealDeliverySync,
} from "./mealDeliveryTypes";

export async function syncMealDeliveryProvider(
  familyId: string,
  providerKey: MealDeliveryProviderKey,
  query?: string,
  limit = 30,
): Promise<MealDeliverySync> {
  const response = await fetch(
    buildApiUrl(
      `/api/families/${encodeURIComponent(familyId)}/meal-discovery/providers/${providerKey}/sync`,
    ),
    {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        query: query?.trim() || null,
        limit,
      }),
    },
  );
  if (!response.ok) {
    let message = response.statusText || `HTTP ${response.status}`;
    try {
      const payload = (await response.json()) as { detail?: unknown };
      if (typeof payload.detail === "string" && payload.detail) message = payload.detail;
    } catch {
      // Keep the HTTP fallback.
    }
    throw new ApiError(message, response.status);
  }
  return (await response.json()) as MealDeliverySync;
}
