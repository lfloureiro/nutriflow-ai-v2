import { ApiError, buildApiUrl } from "./client";
import type {
  RestaurantDiscovery,
  RestaurantMenuSync,
  RestaurantMenuSyncRequest,
} from "./restaurantDiscoveryTypes";

async function responseJson<T>(response: Response): Promise<T> {
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

export async function discoverRestaurants(
  familyId: string,
  area?: string,
  limit = 12,
): Promise<RestaurantDiscovery> {
  const query = new URLSearchParams({ limit: String(limit) });
  if (area?.trim()) query.set("area", area.trim());
  const response = await fetch(
    buildApiUrl(
      `/api/families/${encodeURIComponent(familyId)}/restaurant-discovery?${query.toString()}`,
    ),
    { headers: { Accept: "application/json" } },
  );
  return responseJson<RestaurantDiscovery>(response);
}

export async function syncRestaurantMenus(
  familyId: string,
  request: RestaurantMenuSyncRequest = {},
): Promise<RestaurantMenuSync> {
  const response = await fetch(
    buildApiUrl(`/api/families/${encodeURIComponent(familyId)}/restaurant-menus/sync`),
    {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        area: request.area?.trim() || null,
        restaurant_limit: request.restaurant_limit ?? 8,
        item_limit_per_restaurant: request.item_limit_per_restaurant ?? 60,
      }),
    },
  );
  return responseJson<RestaurantMenuSync>(response);
}
