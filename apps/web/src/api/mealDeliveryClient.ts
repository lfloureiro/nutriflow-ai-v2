import { ApiError, buildApiUrl } from "./client";
import type {
  MealDeliveryMenuItem,
  MealDeliveryProviderKey,
  MealDeliverySync,
} from "./mealDeliveryTypes";

export function mealDeliveryItemsPath(
  familyId: string,
  providerKey: MealDeliveryProviderKey,
): string {
  return `/api/families/${encodeURIComponent(familyId)}/meal-discovery/providers/${providerKey}/items`;
}

export function mealDeliverySyncPath(
  familyId: string,
  providerKey: MealDeliveryProviderKey,
): string {
  return `/api/families/${encodeURIComponent(familyId)}/meal-discovery/providers/${providerKey}/sync`;
}

async function readResponse<T>(response: Response): Promise<T> {
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
  return (await response.json()) as T;
}

export async function listMealDeliveryProviderItems(
  familyId: string,
  providerKey: MealDeliveryProviderKey,
  limit = 100,
): Promise<MealDeliveryMenuItem[]> {
  const query = new URLSearchParams({ limit: String(limit) });
  const response = await fetch(
    buildApiUrl(`${mealDeliveryItemsPath(familyId, providerKey)}?${query.toString()}`),
    { headers: { Accept: "application/json" } },
  );
  return readResponse<MealDeliveryMenuItem[]>(response);
}

export async function syncMealDeliveryProvider(
  familyId: string,
  providerKey: MealDeliveryProviderKey,
  query?: string,
  limit = 30,
): Promise<MealDeliverySync> {
  const response = await fetch(buildApiUrl(mealDeliverySyncPath(familyId, providerKey)), {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      query: query?.trim() || null,
      limit,
    }),
  });
  return readResponse<MealDeliverySync>(response);
}
