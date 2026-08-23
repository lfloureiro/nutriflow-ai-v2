import { ApiError, buildApiUrl } from "./client";
import type { RestaurantDiscovery } from "./restaurantDiscoveryTypes";

export async function discoverRestaurants(
  familyId: string,
  area: string,
  limit = 12,
): Promise<RestaurantDiscovery> {
  const query = new URLSearchParams({ area, limit: String(limit) });
  const response = await fetch(
    buildApiUrl(
      `/api/families/${encodeURIComponent(familyId)}/restaurant-discovery?${query.toString()}`,
    ),
    { headers: { Accept: "application/json" } },
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
  return (await response.json()) as RestaurantDiscovery;
}
