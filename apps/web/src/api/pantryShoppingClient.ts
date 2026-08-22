import { ApiError, buildApiUrl } from "./client";
import type {
  PantryLot,
  PantryLotCreate,
  PantryLotUpdate,
  ShoppingList,
  ShoppingListItemCreate,
  ShoppingListItemUpdate,
} from "./pantryShoppingTypes";

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
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export function familyPantryPath(familyId: string, includeInactive = false): string {
  const base = `/api/families/${encodeURIComponent(familyId)}/pantry`;
  return includeInactive ? `${base}?include_inactive=true` : base;
}

export function familyShoppingListPath(familyId: string): string {
  return `/api/families/${encodeURIComponent(familyId)}/shopping-list`;
}

export function listPantryLots(familyId: string, includeInactive = false): Promise<PantryLot[]> {
  return request<PantryLot[]>(familyPantryPath(familyId, includeInactive));
}

export function createPantryLot(familyId: string, payload: PantryLotCreate): Promise<PantryLot> {
  return request<PantryLot>(familyPantryPath(familyId), {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updatePantryLot(
  familyId: string,
  lotId: string,
  payload: PantryLotUpdate,
): Promise<PantryLot> {
  return request<PantryLot>(`${familyPantryPath(familyId)}/${encodeURIComponent(lotId)}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function deactivatePantryLot(familyId: string, lotId: string): Promise<void> {
  return request<void>(`${familyPantryPath(familyId)}/${encodeURIComponent(lotId)}`, {
    method: "DELETE",
  });
}

export function getShoppingList(familyId: string): Promise<ShoppingList> {
  return request<ShoppingList>(familyShoppingListPath(familyId));
}

export function refreshShoppingList(
  familyId: string,
  startDate: string,
  days: number,
): Promise<ShoppingList> {
  return request<ShoppingList>(`${familyShoppingListPath(familyId)}/refresh`, {
    method: "POST",
    body: JSON.stringify({ start_date: startDate, days }),
  });
}

export function addShoppingItem(
  familyId: string,
  payload: ShoppingListItemCreate,
): Promise<ShoppingList> {
  return request<ShoppingList>(`${familyShoppingListPath(familyId)}/items`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateShoppingItem(
  familyId: string,
  itemId: string,
  payload: ShoppingListItemUpdate,
): Promise<ShoppingList> {
  return request<ShoppingList>(
    `${familyShoppingListPath(familyId)}/items/${encodeURIComponent(itemId)}`,
    { method: "PATCH", body: JSON.stringify(payload) },
  );
}

export function deleteShoppingItem(familyId: string, itemId: string): Promise<void> {
  return request<void>(
    `${familyShoppingListPath(familyId)}/items/${encodeURIComponent(itemId)}`,
    { method: "DELETE" },
  );
}
