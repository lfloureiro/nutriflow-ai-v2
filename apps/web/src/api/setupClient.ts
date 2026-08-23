import { ApiError, buildApiUrl } from "./client";
import type {
  CreatedPerson,
  Family,
  FamilyCreate,
  FamilyUpdate,
  MealDiscoveryCapabilities,
  PersonCreate,
  PersonEnergyProfile,
  PersonMealDiscovery,
  PersonMealDiscoveryUpdate,
} from "./setupTypes";
import type { Person, PlanningBootstrap } from "./types";

async function setupRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  headers.set("Accept", "application/json");
  if (init?.body !== undefined) headers.set("Content-Type", "application/json");
  const response = await fetch(buildApiUrl(path), { ...init, headers });
  if (!response.ok) {
    let message = response.statusText || `HTTP ${response.status}`;
    try {
      const payload = (await response.json()) as { detail?: unknown };
      if (typeof payload.detail === "string" && payload.detail) message = payload.detail;
    } catch {
      // Keep HTTP fallback.
    }
    throw new ApiError(message, response.status);
  }
  return (await response.json()) as T;
}

export function createFamily(payload: FamilyCreate): Promise<Family> {
  return setupRequest<Family>("/api/families", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getFamily(familyId: string): Promise<Family> {
  return setupRequest<Family>(`/api/families/${encodeURIComponent(familyId)}`);
}

export function updateFamily(familyId: string, payload: FamilyUpdate): Promise<Family> {
  return setupRequest<Family>(`/api/families/${encodeURIComponent(familyId)}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function getMealDiscoveryCapabilities(
  familyId: string,
): Promise<MealDiscoveryCapabilities> {
  return setupRequest<MealDiscoveryCapabilities>(
    `/api/families/${encodeURIComponent(familyId)}/meal-discovery-capabilities`,
  );
}

export function createFamilyPerson(familyId: string, payload: PersonCreate): Promise<CreatedPerson> {
  return setupRequest<CreatedPerson>(`/api/families/${encodeURIComponent(familyId)}/persons`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getPerson(personId: string): Promise<Person> {
  return setupRequest<Person>(`/api/persons/${encodeURIComponent(personId)}`);
}

export function getPersonEnergyProfile(personId: string): Promise<PersonEnergyProfile> {
  return setupRequest<PersonEnergyProfile>(
    `/api/persons/${encodeURIComponent(personId)}/energy-profile`,
  );
}

export function getPersonMealDiscovery(personId: string): Promise<PersonMealDiscovery> {
  return setupRequest<PersonMealDiscovery>(
    `/api/persons/${encodeURIComponent(personId)}/meal-discovery`,
  );
}

export function updatePersonMealDiscovery(
  personId: string,
  payload: PersonMealDiscoveryUpdate,
): Promise<PersonMealDiscovery> {
  return setupRequest<PersonMealDiscovery>(
    `/api/persons/${encodeURIComponent(personId)}/meal-discovery`,
    {
      method: "PUT",
      body: JSON.stringify(payload),
    },
  );
}

export function getPersonPlanningContext(
  personId: string,
  scheduledAt: string,
): Promise<PlanningBootstrap> {
  const query = new URLSearchParams({ scheduled_at: scheduledAt, ensure_state: "true" });
  return setupRequest<PlanningBootstrap>(
    `/api/persons/${encodeURIComponent(personId)}/planning-bootstrap?${query.toString()}`,
  );
}
